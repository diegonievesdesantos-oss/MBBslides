"""README numbers are GENERATED from evals/results/latest.json (the single source of truth).

    scripts/cpe results readme           rewrite the block between the metrics markers
    scripts/cpe results readme --check   exit 1 if the committed README disagrees with latest.json (CI)

Nobody edits scores by hand in the README any more. Frozen numbers of past
releases live in CHANGELOG.md and evals/results/history/.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LATEST = ROOT / "evals" / "results" / "latest.json"
README = ROOT / "README.md"
START, END = "<!-- metrics:start (generated from evals/results/latest.json by `cpe results readme`; do not edit) -->", "<!-- metrics:end -->"


def _f(v, nd=1):
    return "—" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def render_block(data: dict) -> str:
    reg = data.get("regression") or {}
    hold = (data.get("holdout") or {}).get("public") or {}
    priv = (data.get("holdout") or {}).get("private") or {}
    hum = data.get("human_reference") or {}
    ex = (data.get("examples") or {}).get("cases") or {}
    env = data.get("environment") or {}
    L = [START, "", "Three independent signals, never combined into one number ([why](docs/EVALS.md)):", "",
         "| signal | what it measures | current |", "|---|---|---|"]
    metric = reg.get("metric") or "composition"
    L.append(f"| **Regression** | {metric} over the development suite ({reg.get('cases_total', '—')} decks, {reg.get('slides_measured', '—')} slides); gates CI | "
             f"**{_f(reg.get('suite_composition'))}**/100 · QA errors {_f(reg.get('qa_errors'))} |")
    if hold:
        blind = "" if not hold.get("note") else " — **no longer blind**: " + hold["note"]
        L.append(f"| **Holdout** | {hold.get('metric') or 'same metric'} on public cases kept out of development ({hold.get('cases_total')} decks, {hold.get('slides_measured')} slides); reported, never tuned on{blind} | "
                 f"**{_f(hold.get('suite_composition'))}**/100 · QA errors {_f(hold.get('qa_errors'))} |")
    else:
        L.append("| **Holdout** | same metric on unseen public cases; reported, never tuned on | not run yet |")
    if hum.get("comparisons"):
        ci = hum.get("challenger_preference_ci95") or [None, None]
        L.append(f"| **Human preference** | blind A/B votes ({hum['comparisons']} comparisons, {hum.get('evaluators')} evaluators) | "
                 f"challenger preferred {_f(hum.get('challenger_preference'), 2)} (95% CI {_f(ci[0], 2)}–{_f(ci[1], 2)}) |")
    else:
        L.append(f"| **Human preference** | blind A/B votes (`cpe human`) | {hum.get('status', 'no votes yet')} |")
    if priv.get("summary"):
        L.append(f"| Private corporate template | brand-ingest understanding of a real corporate template (sanitized) | {priv['summary']} |")
    if ex:
        L += ["", f"| example deck | QA gate | QA score | {(data.get('examples') or {}).get('metric') or 'composition'} |", "|---|---|---|---|"]
        for name, c in ex.items():
            L.append(f"| `{name}` | {'PASSED' if c.get('qa_passed') else 'FAILED'} · {_f(c.get('qa_errors'))} errors · {_f(c.get('qa_warnings'))} warnings | "
                     f"{_f(c.get('qa_score'))} | {_f(c.get('composition'))} |")
    L += ["", f"<sub>engine {data.get('version')} · {env.get('libreoffice', '?')} · fontconfig {env.get('fontconfig', '?')} · "
          f"container `{env.get('container_image') or 'none'}` · render fingerprint `{env.get('fingerprint', '?')}`</sub>", "", END]
    return "\n".join(L)


def update_readme(check: bool = False, readme: Path = README, latest: Path = LATEST) -> bool:
    """Returns True if the README block differs from latest.json (and rewrites it unless check)."""
    data = json.loads(latest.read_text()) if latest.exists() else {}
    txt = readme.read_text()
    if START not in txt or END not in txt:
        raise SystemExit(f"README has no metrics markers ({START} … {END})")
    head, rest = txt.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + render_block(data) + tail
    changed = new != txt
    if changed and not check:
        readme.write_text(new)
    return changed
