# MBBslides reproducible visual environment: the SAME renderer, fonts and Python stack
# for local runs and CI. A render-based benchmark is only meaningful if these are fixed.
#
#   docker build -t mbbslides-visual -f docker/Dockerfile .
#   scripts/cpe-docker eval --suite regression
#
# Determinism:
#   * base image pinned by digest (public.ecr.aws mirror of the official ubuntu image,
#     no Docker Hub rate limits in CI);
#   * apt resolved against a FIXED Ubuntu archive snapshot (snapshot.ubuntu.com), and every
#     render-relevant package pinned to an exact version: a rebuild months later installs
#     byte-identical LibreOffice, fontconfig, FreeType, HarfBuzz and fonts;
#   * Python packages pinned in requirements.lock;
#   * fontconfig cache built at image build time; no user fonts.
# Bump SNAPSHOT + the pins together, deliberately, and re-baseline the evals (docs/REPRODUCIBILITY.md).
ARG BASE_IMAGE=public.ecr.aws/ubuntu/ubuntu:24.04@sha256:f4da486bc9b357039b00eb68d03fdbda5570525a5c14f56907d75fd5aa204f8f
FROM ${BASE_IMAGE}

ARG SNAPSHOT=20260930T000000Z
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 LC_ALL=C.UTF-8 TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 \
    SOURCE_DATE_EPOCH=1790726400 \
    CPE_CONTAINER_IMAGE=mbbslides-visual

# 1) ca-certificates (not render-relevant, pinned) from the base image's archive, so apt can reach
#    the snapshot over HTTPS; 2) switch ALL sources to the fixed snapshot. Package signatures are
#    verified by apt with the Ubuntu archive key in both steps.
ARG CA_CERTIFICATES=20260601~24.04.1
# Optional: behind a TLS-intercepting corporate proxy, pass its CA as a BuildKit secret:
#   docker build --secret id=extra_ca,src=/path/to/ca.pem ...
RUN --mount=type=secret,id=extra_ca,mode=0444 \
    if [ -s /run/secrets/extra_ca ]; then printf 'Acquire::https::CaInfo "/run/secrets/extra_ca";\n' > /etc/apt/apt.conf.d/00extra-ca; fi \
 && apt-get update && apt-get install -y --no-install-recommends ca-certificates=${CA_CERTIFICATES} \
 && rm -f /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list \
 && printf 'Types: deb\nURIs: https://snapshot.ubuntu.com/ubuntu/%s\nSuites: noble noble-updates noble-security\nComponents: main universe\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n' "$SNAPSHOT" > /etc/apt/sources.list.d/snapshot.sources \
 && printf 'Acquire::Check-Valid-Until "false";\nAcquire::Retries "5";\n' > /etc/apt/apt.conf.d/99snapshot \
 && rm -rf /var/lib/apt/lists/* && apt-get update

COPY docker/apt-pins.txt /tmp/apt-pins.txt
RUN --mount=type=secret,id=extra_ca,mode=0444 \
    apt-get install -y --no-install-recommends $(grep -vE '^\s*(#|$)' /tmp/apt-pins.txt | tr '\n' ' ') \
 && apt-get clean && rm -rf /var/lib/apt/lists/* /etc/apt/apt.conf.d/00extra-ca \
 && fc-cache -f && git config --system safe.directory "*"

WORKDIR /opt/mbbslides
COPY requirements.lock ./
RUN --mount=type=secret,id=extra_ca,mode=0444 \
    if [ -s /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi \
 && python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-deps -r requirements.lock
ENV PATH=/opt/venv/bin:$PATH

# the source is bind-mounted at run time (scripts/cpe-docker); the image holds only the environment
WORKDIR /work
ENV PYTHONPATH=/work/src
ENTRYPOINT ["python3", "-m", "cpe"]
