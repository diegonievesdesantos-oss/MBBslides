# v1.8 debt — findings from the real-project acceptance run

**What ran.** Real messy project `proyecto_v18_1`, private, supplied by the owner on 2026-10-02:
- an 11-slide deck presented 11 months earlier;
- 18 new sources: CSV exports with 600+ rows, ledger, two-level budget, memos, emails;
- 5 earlier sources.

It ran end to end on engine commit 45adad5 (1.8.0.dev0), with no engine change during the run:
`deck ingest` → `reason facts` → 6 analysis scripts → protocol 1.4 artifacts → `reason check` → render.

**Result:**
- reasoning check: 0 errors, 0 hard failures;
- render QA: passed, 93.7, 0 errors;
- 12 slides (10 + 2 appendix) on the old deck's style.

The owner's blind review against their sealed answer key is **pending**. Only aggregates are recorded
here; the case stays in `.private/`.

## Findings, by impact

| # | finding | measured | effect |
|---|---|---|---|
| U1 | **`deck stale` precision is low on real material.** | 131 old numbers. "Outdated" status correct in 21 of 36 (58%); suggested new value correct in 1 of 36. "Current" has false positives from coincidental equal values. | The automatic plan is a checklist, not a change plan; the agent must review it. Fix: match on label + unit + period, not value or one shared word; ignore ledger entry numbers and codes; prefer analysis outputs; never call a value "current" just because some other source repeats an old figure. |
| U2 | **Banner line above a two-level header.** | A title line above the header made every budget value "2026 · budget", and line counts read as %. | A.4 works on clean files only. Fix: skip leading title rows (one non-empty cell) before header detection. |
| U3 | **Conflict detection missed every real conflict** and raised one false one. | 0 of 5 real conflicts found (capex 3 versions, productivity 4 versions, savings 3, error rate 2, model vs deck); 1 false positive (a margin % vs a growth %). | Recorded by hand. Fix: compare facts sharing a measure phrase across files, even without a period; never pair different measures. |
| U4 | **Week numbers are not exempt as periods.** | "semanas 31 a 40", "S37" were hard UNSUPPORTED_NUMBER errors until the fact holding them was cited. | Protocol 1.4 says periods are exempt. Fix: treat ISO week references (semana / week / S + 1-53) as periods. |
| U5 | **Render QA and reasoning check disagree on dates in headlines.** | "27 de noviembre" is a HEADLINE_NUMBER_UNSUPPORTED warning in render QA, while the reasoning check passes. | Fix: apply the protocol 1.4 date exemption in render QA too. |
| U6 | **Unit labels leak from row labels.** | A row label containing "120 k€" gave EUR_K to a ratio column; "1,91x" read as PCT; a growth note gave PCT to line counts. | Workaround: computed facts with the right unit. Fix: units come from the column header only, never from the row label. |
| U7 | **A deck built with free text boxes gives no corporate layouts.** | 12 of 12 slides fell back to engine layouts. The report states why: the old deck's layouts have no placeholders. Style still came through: typography, palette, grid and chart colours were 100%. | Correct behaviour. Possible feature: learn layouts from a deck's slide geometry when its layouts are empty. |

## What worked as designed

- **Old-deck ingestion:** `deck ingest` read all 11 slides correctly: roles, headlines, tables, line and column charts with data.
- **Analysis scripts:** they handled the messy data, including n/a days, a double-booked ledger entry, decimal comma, two-level budget and fiscal years. Every derived number was citable.
- **Factuality gate:** the gate blocked 31 numbers on the first check. All were fixed by citing the right fact, never by deleting content.
- **Cell binding:** 14 chart points were bound to their weekly facts with `"at"`.
- **Corporate run reports:** `corporate_usage.md` and `brand_fidelity.md` were written automatically for the corporate run and gave a correct, explained verdict.

## Status

U1–U6 are engine fixes for the next cycle. They must not be tuned on this case, which is now
development data. U7 is a feature idea.
