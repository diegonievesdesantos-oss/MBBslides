# Reproducibility of the visual benchmark

A render-based score only means something if the renderer is known. v1.2 fixes everything that
can move a pixel and records it with every eval.

## The visual environment (`docker/Dockerfile`)

| layer | how it is fixed |
|---|---|
| base image | `public.ecr.aws/ubuntu/ubuntu:24.04` pinned by **digest** |
| system packages | apt resolves against a fixed **Ubuntu archive snapshot** (`SNAPSHOT=20260930T000000Z`, snapshot.ubuntu.com) and every render-relevant package is pinned to an exact version in `docker/apt-pins.txt`: LibreOffice 24.2.7, fontconfig 2.15.0, FreeType 2.13.2, HarfBuzz 8.3.0, FriBiDi 1.0.13, cairo, Python 3.12.3 |
| fonts | Liberation (Arial/Times/Courier metrics), Carlito (Calibri), Caladea (Cambria), DejaVu, and (v1.3) the open-licence corporate typefaces Inter, Roboto, Open Sans, Lato, Montserrat; nothing proprietary — a missing corporate font falls back identically everywhere |
| Python | `requirements.lock` (python-pptx, Pillow, lxml, PyMuPDF, openpyxl … exact versions) |
| process | `LANG=C.UTF-8`, `TZ=UTC`, `PYTHONHASHSEED=0`, fontconfig cache built at image build |

The **same image** runs locally and in CI:

```bash
scripts/cpe-docker eval --suite regression            # builds the image once if missing
scripts/cpe-docker --exec python3 -m pytest -q         # any command
scripts/cpe eval --docker                              # equivalent: re-executes inside the image
CPE_DOCKER_BUILD_ARGS="--secret id=extra_ca,src=ca.pem" scripts/cpe-docker …   # behind a TLS-inspecting proxy
```

A silent source of drift found while building it: Pillow's wheel bundles libraqm (HarfBuzz text
shaping with kerning) but loads FriBiDi from the system. Without FriBiDi it silently falls back
to BASIC layout (no kerning): every measured width shifts by ~0.2% and headline widths change.
FriBiDi is pinned in the image and the layout engine is part of the environment manifest.

## Environment manifest (`src/cpe/environment.py`)

Every `cpe eval` stores in its report (and `--record` in `evals/results/latest.json`): OS, Python,
LibreOffice, fontconfig, package versions, Pillow text layout engine, every measurement font file
with its hash, what fontconfig substitutes for common corporate fonts, installed families, engine
version, container image + digest, git commit, and a **render fingerprint** (hash of the
render-relevant part). A regression run warns when its fingerprint differs from the baseline's,
and CI checks that the environment is the one the recorded results were produced in
(`scripts/check_environment.py`, which prints what changed).

## Reproducibility test (`cpe repro`, `tests/test_reproducibility.py`, CI job `reproducibility`)

Same input, same environment, same engine → render twice → compare:

| check | tolerance |
|---|---|
| slide count, PNG dimensions | equal |
| PNG content hash | equal |
| pixel difference | 0 (share of differing pixels) |
| PDF text layout (text, size, position of every span) | equal (±0.01 in) |
| composition metrics (every slide, every metric) | equal (0) |
| QA result (verdict, codes per slide) | equal |

Observed: pixel-identical renders, run to run and between the local environment and the
container once FriBiDi was aligned. No tolerance is needed, so none is used. PDF bytes are not
compared (LibreOffice stamps a date and document id); everything the engine reads from the PDF is.

## Provenance (v1.4)

Every recorded release signal in `evals/results/latest.json` carries `provenance`:
`evaluated_commit`, `git_tree`, `dirty` (+ the dirty paths), `engine_version`, `container_image` /
`container_digest`, `environment_fingerprint` and `eval_timestamp_utc` (run metadata only — never
used inside a render). A run on a dirty tree cannot become release truth: `--record` refuses it
(`--allow-dirty` records it as `release_truth: false` for development, and verification then fails).
Files that a results run *writes* (`evals/results/`, baselines, README/CHANGELOG/docs, human rounds)
do not make the source dirty; everything that determines the numbers does
(`environment.ENGINE_PATHS`: `src/`, `docker/`, `requirements.lock`, `pyproject.toml`, eval cases,
gates, robustness seeds, holdout, example specs).

### Release workflow

```
CODE FREEZE: commit C (engine, version, eval cases, example outputs)
      ↓  on the clean checkout of C, inside the image:
cpe eval --suite regression --update-baseline --record     (provenance: evaluated_commit = C, dirty = false)
cpe eval --suite examples --record
cpe robustness --update-baseline --record
cpe eval --suite holdout_v2 --release-candidate --record   (ONCE)
cpe human build … (r2) ; cpe human status … --record
cpe results readme
      ↓
RESULTS SNAPSHOT: commit R (latest.json, baselines, README, CHANGELOG, docs, human round)
```

`latest.json` lives in R but declares C. CI (`cpe results verify`) checks that every release signal
was evaluated on a clean commit present in history and that no engine input changed between C and
HEAD — results may be committed later, the engine may not.

## Changing the environment deliberately

Bump `SNAPSHOT` and the pins together, rebuild, commit the image definition (commit C), then
follow the release workflow above on C. The fingerprint change makes the reason visible.

## CI (`.github/workflows/ci.yml`)

Runner pinned to `ubuntu-24.04`; actions on the Node 24 runtime pinned to commit SHAs
(checkout v7.0.1, setup-python v7.0.0, upload-artifact v7.0.1, buildx v4.4.1, build-push v7.4.0,
login v4.6.0 — versions checked at implementation time). Jobs: `lint` (ruff, README metrics
consistency, results provenance, battery generator up to date), `package` (wheel builds and works
outside the checkout), `image` (builds the visual environment once and publishes it to GHCR),
`tests`, `regression` (regression suite vs baseline + absolute archetype gates + example decks),
`quality_profile` (archetype battery → quality profile, absolute gates, diagnostics and contact
sheets as artifacts), `robustness` (metamorphic suite vs its baseline), `reproducibility`
(render-twice checks + environment check) — all rendering inside the image. The sealed holdout
never runs in CI.
