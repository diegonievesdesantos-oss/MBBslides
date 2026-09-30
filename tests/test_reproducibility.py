"""Reproducibility: a render-based benchmark must mean the same thing over time."""
import json
import re
from pathlib import Path

from conftest import ROOT, content_slide, mini_spec, needs_render
from cpe import environment
from cpe.reproducibility import check


def test_ci_uses_a_pinned_runner_and_node24_actions():
    wf = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert not re.search(r"runs-on:\s*ubuntu-latest", wf)
    runners = re.findall(r"runs-on:\s*(\S+)", wf)
    assert runners and all(r == "ubuntu-24.04" for r in runners)
    uses = re.findall(r"uses:\s*(\S+)@(\S+)", wf)
    assert uses
    for action, ref in uses:
        assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{action} must be pinned to a commit SHA, got {ref}"
    # versions known to run on Node 24 (checked at implementation time; see docs/REPRODUCIBILITY.md)
    for action, minimum in {"actions/checkout": 6, "actions/setup-python": 6, "actions/upload-artifact": 6}.items():
        for m in re.findall(rf"uses:\s*{action}@\S+\s*#\s*v(\d+)", wf):
            assert int(m) >= minimum


def test_docker_environment_is_pinned():
    df = (ROOT / "docker" / "Dockerfile").read_text()
    assert re.search(r"BASE_IMAGE=\S+@sha256:[0-9a-f]{64}", df), "base image must be pinned by digest"
    assert re.search(r"ARG SNAPSHOT=\d{8}T\d{6}Z", df), "apt must resolve against a fixed archive snapshot"
    pins = [line.strip() for line in (ROOT / "docker" / "apt-pins.txt").read_text().splitlines() if line.strip() and not line.startswith("#")]
    need = {"libreoffice-impress", "libreoffice-core", "fontconfig", "fonts-liberation", "fonts-crosextra-carlito", "fonts-crosextra-caladea", "libfreetype6", "libharfbuzz0b", "libfribidi0"}
    pinned = {p.split("=")[0] for p in pins if "=" in p}
    assert need <= pinned, f"unpinned render packages: {need - pinned}"
    lock = (ROOT / "requirements.lock").read_text()
    for pkg in ("python-pptx", "pillow", "lxml", "pymupdf"):
        assert re.search(rf"^{pkg}==\S+", lock, re.M | re.I)


def test_environment_manifest_fields_and_diff():
    m = environment.manifest()
    for k in ("os", "python", "libreoffice", "fontconfig", "fonts", "cpe_version", "container_image", "commit", "text_layout_engine", "fingerprint"):
        assert k in m
    assert environment.fingerprint(m) == m["fingerprint"]  # stable
    other = json.loads(json.dumps(m))
    other["libreoffice"] = "LibreOffice 99.0"
    other["fonts"][0]["sha256"] = "0" * 16
    assert environment.fingerprint(other) != m["fingerprint"]
    d = "\n".join(environment.diff(m, other))
    assert "libreoffice" in d and "font file" in d


@needs_render
def test_same_input_same_environment_renders_identically(tmp_path):
    spec = mini_spec([
        content_slide(id="r1"),
        content_slide(id="r2", headline="Two options remain after the screen and the board picks one in June",
                      message_type="comparison", evidence=[],
                      visual={"type": "table", "title": "Options", "columns": [{"label": "Option"}, {"label": "NPV (€M)", "kind": "number"}],
                              "rows": [["Build", 120], ["Buy", 95]]}),
    ])
    r = check(spec, tmp_path, dpi=60)
    assert r["passed"], json.dumps(r["checks"])
    assert r["worst_pixel_diff_share"] == 0.0  # the pinned renderer is deterministic: exact equality, no tolerance needed
    assert Path(tmp_path / "repro_report.json").exists()
