"""README numbers are GENERATED from evals/results/latest.json (the single source of truth).

    scripts/cpe results readme           rewrite the block between the metrics markers
    scripts/cpe results readme --check   exit 1 if the committed README disagrees with latest.json (CI)
    scripts/cpe results verify           exit 1 unless every release signal was evaluated on a clean commit
                                         whose engine inputs are identical to HEAD (CI; docs/REPRODUCIBILITY.md)

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


def _verdict(v):
    return "—" if v is None else ("passed" if v else "FAILED")


def _pct(v):
    return "—" if v is None else f"{round(100 * v)}%"


def render_block(data: dict) -> str:
    reg = data.get("regression") or {}
    hold = data.get("holdout") or {}
    v2 = hold.get("v2") or {}
    v1 = hold.get("v1_historical") or {}
    priv = data.get("development_private") or hold.get("private") or {}
    hum = data.get("human_reference") or {}
    rob = data.get("robustness") or {}
    ex = (data.get("examples") or {}).get("cases") or {}
    env = data.get("environment") or {}
    o = reg.get("overall") or {}
    dist = reg.get("distribution") or {}
    gates = reg.get("absolute_gates") or {}
    cov = gates.get("coverage") or {}
    L = [START, "", "Independent signals, never combined into one number ([why](docs/EVALS.md)). A mean hides structure, so the regression "
         "signal is reported as a distribution across slide archetypes.", "",
         "**Regression** — development suite, gates CI (relative baseline + absolute archetype gates)", "",
         "| measure | value |", "|---|---|",
         f"| overall (mean of decks, historical continuity) | {_f(reg.get('suite_composition'))} |",
         f"| macro archetype (each archetype weighs the same) | **{_f(o.get('macro_archetype_score'))}** |",
         f"| weakest archetype | **{o.get('weakest_archetype', '—')} {_f(o.get('weakest_archetype_score'))}** |",
         f"| P10 slide | **{_f(dist.get('p10'))}** (median {_f(dist.get('median'))}) |",
         f"| slides ≥ 80 / ≥ 70 | {_pct(o.get('share_slides_above_80'))} / {_pct(o.get('share_slides_above_70'))} |",
         f"| archetypes gate-eligible (n ≥ 8) | {len(cov.get('gate_eligible') or [])} of {cov.get('of', 17)} |",
         f"| archetypes not healthy | {', '.join(gates.get('not_healthy') or []) or 'none'} |",
         f"| QA errors (visual / authoring lint) | {_f(o.get('qa_errors_visual'))} / {_f(reg.get('qa_errors_authoring'))} |",
         f"| slides authored · resolved · measured · decks | {_f(reg.get('slides_authored'))} · {_f(reg.get('slides_resolved'))} · "
         f"{_f(reg.get('slides_measured'))} · {_f(reg.get('cases_total'))} |",
         f"| visual QA · authoring QA · benchmark | {_verdict(reg.get('visual_qa_passed'))} · {_verdict(reg.get('authoring_qa_passed'))} · "
         f"{_verdict(reg.get('benchmark_passed'))} |", ""]
    L += ["| other signal | what it measures | current |", "|---|---|---|"]
    if v2.get("suite_composition") is not None:
        vo = v2.get("overall") or {}
        L.append(f"| **Holdout v2** | sealed at v1.4, run once (v1.4.0); development-known since v1.5 ({v2.get('cases_total')} decks, "
                 f"{_f(v2.get('slides_authored'))} authored / {_f(v2.get('slides_measured'))} measured slides) | "
                 f"overall {_f(v2.get('suite_composition'))} · macro {_f(vo.get('macro_archetype_score'))} · P10 {_f((v2.get('distribution') or {}).get('p10'))} · "
                 f"weakest {vo.get('weakest_archetype')} {_f(vo.get('weakest_archetype_score'))} |")
    else:
        L.append("| **Holdout v2** | sealed, never tuned on, run once per release candidate | NOT RUN YET |")
    if rob.get("variants"):
        L.append(f"| **Robustness** | small content perturbations of development seeds ({rob['variants']} variants) | median drop {_f(rob.get('median_drop'))} · "
                 f"P90 drop {_f(rob.get('p90_drop'))} · catastrophic {rob.get('catastrophic')} ({_pct(rob.get('catastrophic_rate'))}) |")
    else:
        L.append("| **Robustness** | small content perturbations of development seeds | not run yet |")
    for rnd in ("r1", "r2"):
        h = (hum.get("rounds") or {}).get(rnd) or {}
        if h.get("comparisons"):
            ci = h.get("challenger_preference_ci95") or [None, None]
            sa = h.get("score_agreement") or {}
            L.append(f"| **Human {rnd}** | blind A/B votes ({h['comparisons']} votes, {h.get('evaluators')} evaluators){' — development data' if h.get('used_for_calibration') else ''} | "
                     f"challenger preferred {_f(h.get('challenger_preference'), 2)} (95% CI {_f(ci[0], 2)}–{_f(ci[1], 2)}) · scorer agrees {_f(sa.get('rate'), 2)} |")
        elif h:
            L.append(f"| **Human {rnd}** | blind A/B votes (`cpe human`) | {h.get('status', 'awaiting human votes')} |")
    if not hum.get("rounds"):
        L.append(f"| **Human** | blind A/B votes (`cpe human`) | {hum.get('status', 'awaiting human votes')} |")
    if v1.get("suite_composition") is not None or v1.get("note"):
        L.append(f"| Holdout v1 (retired) | H01–H05, development-known since v1.3 | last blind result 81.0 (v1.2); {v1.get('note', '')} |")
    if priv.get("summary"):
        L.append(f"| Private corporate template — **development data, not a holdout** | brand-ingest understanding of a real corporate template (sanitized) | {priv['summary']} |")
    if ex:
        L += ["", "Example decks are development material and regression fixtures, not evidence of generalization:", "",
              f"| example deck | QA gate | QA score | {(data.get('examples') or {}).get('metric') or 'composition'} |", "|---|---|---|---|"]
        for name, c in ex.items():
            L.append(f"| `{name}` | {'PASSED' if c.get('qa_passed') else 'FAILED'} · {_f(c.get('qa_errors'))} errors · {_f(c.get('qa_warnings'))} warnings | "
                     f"{_f(c.get('qa_score'))} | {_f(c.get('composition'))} |")
    pv = reg.get("provenance") or {}
    src_dirty = pv.get("evaluated_source_dirty", pv.get("dirty"))
    L += ["", f"<sub>engine {data.get('version')} · evaluated source commit `{(pv.get('evaluated_source_commit') or pv.get('evaluated_commit') or '?')[:10]}`"
          f"{' (evaluated source DIRTY: not release truth)' if src_dirty else ''} · "
          f"{env.get('libreoffice', '?')} · fontconfig {env.get('fontconfig', '?')} · container `{env.get('container_image') or 'none'}` · "
          f"render fingerprint `{env.get('fingerprint', '?')}`</sub>", "", END]
    return "\n".join(L)


RELEASE_SECTIONS = ("regression", "examples", "robustness")


def verify_provenance(data: dict | None = None, latest: Path = LATEST) -> list[str]:
    """Release truth check (CI): every recorded release signal was evaluated on a CLEAN commit, and
    nothing that determines the numbers (environment.ENGINE_PATHS) changed between that commit and
    HEAD. Results may be committed later (a results-snapshot commit), the engine may not."""
    import subprocess

    from .environment import ENGINE_PATHS

    data = data if data is not None else (json.loads(latest.read_text()) if latest.exists() else {})
    problems = []
    sections = {k: data.get(k) for k in RELEASE_SECTIONS}
    if (data.get("holdout") or {}).get("v2"):
        sections["holdout.v2"] = data["holdout"]["v2"]
    for name, sec in sections.items():
        if not sec:
            problems.append(f"{name}: not recorded")
            continue
        pv = sec.get("provenance") or {}
        c = pv.get("evaluated_commit")
        if not c:
            problems.append(f"{name}: no evaluated_commit (recorded before v1.4 provenance)")
            continue
        if pv.get("dirty") or not pv.get("release_truth", True):
            problems.append(f"{name}: evaluated on a dirty tree ({c[:10]}) — not release truth")
            continue
        known = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{c}^{{commit}}"], capture_output=True).returncode == 0
        if not known:
            problems.append(f"{name}: evaluated commit {c[:10]} not in this repository's history")
            continue
        diff = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", c, "HEAD", "--", *ENGINE_PATHS], capture_output=True, text=True).stdout.split()
        if diff:
            problems.append(f"{name}: engine inputs changed since {c[:10]} ({', '.join(diff[:5])}{'…' if len(diff) > 5 else ''}) — re-run on the current commit")
    return problems


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
