#!/usr/bin/env python3
"""Fail if the render environment differs from the one evals/results/latest.json was recorded in.

Scores are only comparable within one environment fingerprint (docs/REPRODUCIBILITY.md). When this
fails, the diff names what changed (renderer, fonts, font matching, text layout engine, packages);
rebuild the image from docker/Dockerfile or, for a deliberate environment bump, re-run
`scripts/cpe-docker eval --suite regression --update-baseline --record` and commit both files.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cpe import environment  # noqa: E402

latest = Path(__file__).resolve().parents[1] / "evals" / "results" / "latest.json"
recorded = (json.loads(latest.read_text()) if latest.exists() else {}).get("environment") or {}
now = environment.manifest()
if not recorded:
    print("no recorded environment in evals/results/latest.json")
    sys.exit(1)
if recorded.get("fingerprint") == now["fingerprint"]:
    print(f"environment matches the recorded one (fingerprint {now['fingerprint']})")
    sys.exit(0)
print(f"environment fingerprint {now['fingerprint']} ≠ recorded {recorded.get('fingerprint')}:")
for line in environment.diff(recorded, now):
    print("  " + line)
sys.exit(1)
