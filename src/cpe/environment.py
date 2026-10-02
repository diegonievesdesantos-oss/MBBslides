"""Environment manifest: everything that can change a render, recorded with every eval.

A render-based benchmark only means something if the renderer is known. Every
`cpe eval` writes this manifest next to its results so that any future score
difference can be explained (engine change vs renderer / font / library change).

`fingerprint` hashes the render-relevant part (renderer, fonts, font-matching,
imaging libraries) — two runs with the same fingerprint and the same engine
commit are expected to produce pixel-identical PNGs (tests/test_reproducibility.py).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from . import __version__

ROOT = Path(__file__).resolve().parents[2]

# font names whose resolution changes renders of the public fixtures
PROBE_FONTS = ["Arial", "Calibri", "Cambria", "Georgia", "Times New Roman", "Helvetica", "Inter", "Segoe UI"]
PY_PACKAGES = ["python-pptx", "pillow", "lxml", "pymupdf", "openpyxl"]


def _run(cmd: list[str], timeout: int = 60) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return (r.stdout or r.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


def _os() -> str:
    try:
        rel = Path("/etc/os-release").read_text(encoding="utf-8")
        m = re.search(r'^PRETTY_NAME="?([^"\n]+)', rel, re.M)
        if m:
            return f"{m.group(1)} ({platform.machine()})"
    except OSError:
        pass
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


@lru_cache(maxsize=1)
def libreoffice_version() -> str:
    from .render.renderer import find_soffice

    so = find_soffice()
    return _run([so, "--version"]) if so else "not installed"


def fontconfig_version() -> str:
    out = _run(["fc-match", "--version"])
    m = re.search(r"version\s+([\d.]+)", out)
    return m.group(1) if m else (out or "not installed")


def _pkg_versions() -> dict:
    from importlib import metadata

    out = {}
    for p in PY_PACKAGES:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = None
    return out


def _file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def text_layout_engine() -> str:
    """Pillow's text layout engine: 'raqm' (HarfBuzz shaping + kerning, like LibreOffice) or 'basic'.
    It silently depends on FriBiDi being installed and changes every measured width."""
    from PIL import features

    return f"raqm {features.version('raqm')}" if features.check("raqm") else "basic (no kerning: install libfribidi0)"


def fonts() -> list[dict]:
    """Font files the measurement layer uses (family → file + content hash)."""
    from .design import text_metrics as tm

    out = []
    for fam in sorted(tm.FONT_FILES):
        for bold in (False, True):
            p = tm._font_path(fam, bold)
            out.append({"family": fam, "bold": bold, "file": os.path.basename(p) if p else None, "sha256": _file_sha(p) if p else None})
    return out


def font_matching() -> dict:
    """What fontconfig (hence LibreOffice) draws for each probe name."""
    return {f: _run(["fc-match", "-f", "%{family[0]}|%{file}", f]) or None for f in PROBE_FONTS}


def installed_font_families() -> list[str]:
    out = _run(["fc-list", ":", "family"])
    return sorted({line.split(",")[0].strip() for line in out.splitlines() if line.strip()})


def git_commit() -> str | None:
    """HEAD, suffixed "-dirty" only when the EVALUATED SOURCE changed (engine, cases, profiles…).
    Result files written by a run (RESULT_PATHS) do not make it dirty (v1.5)."""
    c = _run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    if not re.fullmatch(r"[0-9a-f]{40}", c or ""):
        return None
    return c + ("-dirty" if dirty_paths() else "")


def working_tree_dirty() -> bool:
    """Any tracked change at all, results included (reported, never used as release truth)."""
    return bool(_run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"]))


# Files a results run WRITES (and the docs that quote it): a change here does not make the evaluated
# source dirty. Everything else tracked — engine, layouts, profiles, eval cases, image recipe — does.
RESULT_PATHS = ("evals/results/", "evals/regression/baseline.json", "evals/robustness/baseline.json", "README.md", "CHANGELOG.md", "docs/",
                "evals/human_reference/rounds/")
# What determines the numbers: if none of these changed between the evaluated commit and HEAD, the
# recorded results still describe HEAD (results_report.verify_provenance).
ENGINE_PATHS = ("src", "docker", "requirements.lock", "pyproject.toml", "evals/regression/cases", "evals/archetype_gates.json", "evals/robustness/seeds.json",
                "evals/holdout", "examples/alvora/deck.json", "examples/gallery/deck.json", "examples/brand", "scripts/cpe-docker",
                "evals/editorial")


def dirty_paths() -> list[str]:
    out = _run(["git", "-C", str(ROOT), "diff", "--name-only", "HEAD"]) or ""  # staged + unstaged changes to tracked files
    paths = [line.strip() for line in out.splitlines() if line.strip()]
    return [p for p in paths if not p.startswith(RESULT_PATHS)]


def provenance() -> dict:
    """Where a set of numbers comes from: the immutable source it was evaluated on, the image, the
    environment, and when the evaluation ran (run metadata only — never used inside a render)."""
    import datetime

    c = _run(["git", "-C", str(ROOT), "rev-parse", "HEAD"])
    commit = c if re.fullmatch(r"[0-9a-f]{40}", c or "") else None
    tree = _run(["git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"]) if commit else None
    dp = dirty_paths() if commit else []
    return {
        "evaluated_commit": commit, "git_tree": tree or None, "dirty": bool(dp) or commit is None, "dirty_paths": dp[:20],
        # v1.5 terminology: the source the numbers describe vs the checkout they were written from
        "evaluated_source_commit": commit, "evaluated_source_dirty": bool(dp) or commit is None,
        "working_tree_commit": commit, "working_tree_dirty": working_tree_dirty() if commit else None,
        "engine_version": __version__, "container_image": os.environ.get("CPE_CONTAINER_IMAGE"), "container_digest": os.environ.get("CPE_CONTAINER_DIGEST"),
        "eval_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def container_image() -> str | None:
    img = os.environ.get("CPE_CONTAINER_IMAGE")
    if not img:
        return None
    digest = os.environ.get("CPE_CONTAINER_DIGEST")
    return f"{img}@{digest}" if digest else img


def manifest() -> dict:
    env = {
        "os": _os(),
        "python": sys.version.split()[0],
        "libreoffice": libreoffice_version(),
        "fontconfig": fontconfig_version(),
        "packages": _pkg_versions(),
        "text_layout_engine": text_layout_engine(),
        "fonts": fonts(),
        "font_matching": font_matching(),
        "installed_font_families": installed_font_families(),
        "cpe_version": __version__,
        "container_image": container_image(),
        "commit": git_commit(),
    }
    env["fingerprint"] = fingerprint(env)
    env["provenance"] = provenance()
    env["provenance"]["environment_fingerprint"] = env["fingerprint"]
    return env


def fingerprint(env: dict) -> str:
    """Hash of the render-relevant environment (not the engine commit)."""
    keep = {k: env.get(k) for k in ("libreoffice", "fontconfig", "packages", "text_layout_engine", "fonts", "font_matching", "installed_font_families")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()[:16]


def diff(a: dict, b: dict) -> list[str]:
    """Human-readable differences between two manifests (why scores may differ)."""
    out = []
    for k in ("os", "python", "libreoffice", "fontconfig", "text_layout_engine", "container_image", "cpe_version", "commit"):
        if a.get(k) != b.get(k):
            out.append(f"{k}: {a.get(k)} → {b.get(k)}")
    for k in ("packages", "font_matching"):
        for n in sorted(set(a.get(k) or {}) | set(b.get(k) or {})):
            if (a.get(k) or {}).get(n) != (b.get(k) or {}).get(n):
                out.append(f"{k}.{n}: {(a.get(k) or {}).get(n)} → {(b.get(k) or {}).get(n)}")
    fa = {(f["family"], f["bold"]): f["sha256"] for f in a.get("fonts") or []}
    fb = {(f["family"], f["bold"]): f["sha256"] for f in b.get("fonts") or []}
    for key in sorted(set(fa) | set(fb)):
        if fa.get(key) != fb.get(key):
            out.append(f"font file {key[0]}{' bold' if key[1] else ''}: {fa.get(key)} → {fb.get(key)}")
    ia, ib = set(a.get("installed_font_families") or []), set(b.get("installed_font_families") or [])
    if ia != ib:
        out.append(f"installed font families: +{sorted(ib - ia)} −{sorted(ia - ib)}")
    return out
