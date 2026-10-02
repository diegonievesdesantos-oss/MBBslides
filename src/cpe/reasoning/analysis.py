"""Analyses over row-level data: the agent's scripts, run and recorded so their outputs become facts.

Raw data (30.000 orders, a CRM export, an ERP ledger) cannot be read cell by cell into a fact model,
and an insight about it ("on-time delivery fell where pick time rose") needs aggregation. The agent
writes a script; this module runs it, twice, in a clean output folder, and records:

    work/analysis.json   [{name, script, script_sha256, inputs: {file: sha256}, outputs: {file: sha256},
                           reproducible: bool, ran_at}]
    work/analysis/out/<name>/*.csv   the script's output tables

`cpe reason facts` then reads the output tables as sources (`analysis/<name>/<file>`), so every number
derived from the raw data has a fact id, a lineage to a script and to the hashed inputs, and is
grounded like any other. `cpe reason check` blocks the deck when an output no longer matches its
recorded hash, or when the script or an input changed after the run (ANALYSIS_STALE), or when the
script did not reproduce its own outputs (ANALYSIS_NOT_REPRODUCIBLE).

The script contract: read inputs from the folder in $CPE_SOURCES, write CSV tables (header row, one
measure per column, labels in the first columns) to $CPE_OUT. Nothing else is read from it.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _run(script: Path, sources: Path, out: Path, timeout: int) -> subprocess.CompletedProcess:
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CPE_SOURCES": str(sources.resolve()), "CPE_OUT": str(out.resolve()), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, str(script.resolve())], cwd=str(out.parent), env=env, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


def run_analysis(work_dir: str | Path, script: str | Path, sources_dir: str | Path, timeout: int = 600) -> dict:
    work, script, sources = Path(work_dir), Path(script), Path(sources_dir)
    name = script.stem
    out = work / "analysis" / "out" / name
    if out.exists():
        shutil.rmtree(out)
    r = _run(script, sources, out, timeout)
    if r.returncode != 0:
        raise RuntimeError(f"analysis {name} failed:\n{r.stderr[-2000:]}")
    outputs = {p.name: _sha(p) for p in sorted(out.glob("*.csv"))}
    if not outputs:
        raise RuntimeError(f"analysis {name} wrote no CSV to $CPE_OUT")
    with tempfile.TemporaryDirectory() as td:  # a second run must give the same tables
        r2 = _run(script, sources, Path(td) / "out", timeout)
        again = {p.name: _sha(p) for p in sorted((Path(td) / "out").glob("*.csv"))} if r2.returncode == 0 else {}
    entry = {"name": name, "script": str(script), "script_sha256": _sha(script),
             "inputs": {p.name: _sha(p) for p in sorted(sources.rglob("*")) if p.is_file() and not p.name.startswith(".")},
             "outputs": outputs, "reproducible": again == outputs, "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    man_p = work / "analysis.json"
    man = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {"analyses": []}
    man["analyses"] = [a for a in man.get("analyses") or [] if a.get("name") != name] + [entry]
    man_p.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return entry


def output_tables(work_dir: str | Path) -> list[tuple[Path, str]]:
    """(path, source name) of every recorded analysis output, e.g. ('…/out/otd/by_week.csv', 'analysis/otd/by_week.csv')."""
    work = Path(work_dir)
    man_p = work / "analysis.json"
    if not man_p.exists():
        return []
    out = []
    for a in json.loads(man_p.read_text(encoding="utf-8")).get("analyses") or []:
        for f in a.get("outputs") or {}:
            p = work / "analysis" / "out" / a["name"] / f
            if p.exists():
                out.append((p, f"analysis/{a['name']}/{f}"))
    return out


def check_analyses(work_dir: str | Path, sources_dir: str | Path | None) -> list[dict]:
    work = Path(work_dir)
    man_p = work / "analysis.json"
    if not man_p.exists():
        return []
    issues = []

    def issue(code, ref, msg):
        return {"level": "error", "code": code, "artifact": "analysis.json", "ref": ref, "message": msg, "hard": True}

    for a in json.loads(man_p.read_text(encoding="utf-8")).get("analyses") or []:
        n = a.get("name")
        s = Path(a.get("script") or "")
        if not s.is_absolute():  # recorded relative to where `cpe reason analyze` ran (usually the case folder)
            s = next((c for c in (work.parent / s, work / s, s) if c.exists()), s)
        if not s.exists() or _sha(s) != a.get("script_sha256"):
            issues.append(issue("ANALYSIS_STALE", n, "the script changed (or is missing) after its outputs were recorded: re-run `cpe reason analyze`"))
        if sources_dir:
            for f, h in (a.get("inputs") or {}).items():
                p = next(iter(Path(sources_dir).rglob(f)), None)
                if p is None or _sha(p) != h:
                    issues.append(issue("ANALYSIS_STALE", n, f"input {f} changed after the run"))
        for f, h in (a.get("outputs") or {}).items():
            p = work / "analysis" / "out" / n / f
            if not p.exists() or _sha(p) != h:
                issues.append(issue("ANALYSIS_STALE", f"{n}/{f}", "an output table no longer matches what the script produced"))
        if not a.get("reproducible"):
            issues.append(issue("ANALYSIS_NOT_REPRODUCIBLE", n, "a second run of the script gave different tables (randomness, time, unordered output)"))
    return issues
