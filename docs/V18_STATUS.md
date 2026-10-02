# v1.8 — real-world inputs, corporate use, any OS: status

v1.8 makes the engine work on material as it really arrives: messy sources, an existing deck to
update, a corporate template, and a laptop that may run Windows or macOS. Development started on
2026-10-02. Every deterministic part is built and tested. No agent runs were made and no human
evidence was generated. The parts that need the owner are listed at the end.

## Built (deterministic, tested)

| block | item | what it does | evidence |
|---|---|---|---|
| A — messy inputs | A.2 conflicts | names the kind of disagreement: management vs audited, forecast vs actual, definition (group vs local), value, prose | unit tests; real conflicts found on the private cases, no false positives |
| | A.3 periods | FY/CY/Q/H/month/LTM/YTD/run-rate and actual/budget/forecast/audited/management bases; `PERIOD_MISMATCH` warning on incompatible combinations | unit tests |
| | A.4 tables | two-level headers, scenario columns, total / subtotal rows, units per cell, decimal-comma documents | unit tests |
| | A.5 chart data | charts embedded in docx / xlsx / pptx become facts (data caches, Excel references) | unit tests |
| | A.6 existing deck | `cpe deck ingest` (roles, headlines, exhibits with data, every number, conventions; native rebuild including waterfalls) and `cpe deck stale` (current / outdated / untraced per number; keep / update / review per slide) | unit tests; CLI end to end; 12-slide example deck read correctly |
| B — corporate | B.9 usage report | per slide: native, adaptive or engine fallback, with the reason and the rejected layouts (`corporate_usage.md/json`, written by every corporate run) | synthetic multi-master template |
| | B.10 brand fidelity | separate metrics: typography, palette, grid, artwork protection, structural slides, chart styling; layout appropriateness is left to a human (`cpe brand fidelity <run>`) | synthetic template + injected off-brand font, colour and position |
| C — any OS | C.11 portability | UTF-8 for every file the engine reads or writes; LibreOffice and font paths on Windows / macOS; `scripts/cpe.ps1` and `scripts/cpe.cmd`; [INSTALL.md](INSTALL.md); a portability CI on Windows, macOS and Linux | CI workflow `Portability` |
| D — v1.7 leftovers | D.12 cell-to-fact binding | `"at"` on an evidence item binds a fact to a cell (hard); label check on unbound cells (warning) | on the real private deck: 11 of 15 injected swaps flagged, 0 false positives |
| | D.13 visuals | `cause_effect` exhibit; `timeline_decisions` layout; explicit n/a cells and chart points (`n/d` in Spanish) | rendered and inspected; unit tests |

## Real-project acceptance run (2026-10-02)

One real messy project with its previous deck ran end to end. Reasoning check: 0 hard failures. Render QA: 93.7, 0 errors. The owner's blind review against their answer key is pending. Findings, including the low precision of `deck stale` on real material: [DEBT_V18.md](DEBT_V18.md).

## What needs the owner

Step-by-step guide (Spanish) and blank intake templates: [V18_OWNER_BRIEF.md](V18_OWNER_BRIEF.md), [v18_intake/](v18_intake/).

These cannot be done honestly without new material or a human judgement. The engine is ready for each.

1. **3–5 corporate templates the engine has never seen**, ideally from different companies and with
   example slides. Expected result:
   - per template, the usage report (how many slides native / adaptive / fallback, and why);
   - the fidelity metrics;
   - the cases where the engine's choice is wrong.

   Templates stay in `.private/`; only aggregates are recorded.
2. **1–2 real messy projects, ideally with a previous deck.** Expected result:
   - an end-to-end update: old deck → `deck ingest` → new sources → facts → `deck stale` → updated deck;
   - which numbers changed, which were confirmed, which had no source.
3. **The owner's judgement** on the two things no metric can settle:
   - is each slide on the layout a brand designer would choose (layout-family appropriateness)?
   - does the result look like the company's own deck (overall brand fidelity)?
4. **(Optional) A first run of the portability CI** on Windows and macOS. It starts on every push; a
   failure there is a portability bug to fix, never a reason to skip the job.

## Not changed

- Reasoning protocol: 1.5 since 2026-10-02 (five rules from the owner's review of the real-project run, checked as warnings). The v1.8 tooling checks add no agent step.
- Regression, robustness and human evidence: the engine evals are re-run and recorded for this
  version. No human round was run and no vote was generated.
