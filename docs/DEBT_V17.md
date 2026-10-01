# v1.7 debt — final fine-tuning backlog (status after 1.7.1)

v1.7.0 closed on 2026-10-02. Its acceptance test was one real end-to-end case: Grupo Brasa, an external
case written by the owner and kept private. With protocol 1.4 it went from raw ERP data and documents
to an 8-slide Spanish board deck:
- reasoning check: 0 errors, 0 hard failures;
- render QA: 0 errors; deck score 98.1, composition 93.7.

The owner, the expert evaluator, judged the deck "perfect" and asked for the remaining findings to be
kept as debt for a last fine-tuning pass. These are the findings, ordered by impact.

## Factuality (first)

| # | debt | found in | effect |
|---|---|---|---|
| F1 | **Grounding is weak on dense slides**: on a slide that cites ~20 facts, an invented table value usually passes, because "one operation on two cited facts" can produce almost any number. A fake "2,71x" was caught; "777", "944", "3.488" were not. | Brasa deck | An invented number can survive in a table. Fix: ground each table cell or chart value against the facts cited for its row or series, or restrict operations to facts sharing a label, unit and period. |
| F2 | Conflicts between two prose sources are not detected when neither states a period (e.g. a closure cost of 1,5 vs 3,2 M€). On the real cases the detector found none, although the sources disagreed. | s2, s4 cases | Agents record them by hand. |
| F3 | Numbers inside text cells of markdown tables are not extracted ("subida del 22%", "12/18 mensualidades"). | Brasa | Agents parse them in analysis scripts. |
| F4 | Analysis-table headers ending `_k` get no unit, so a true "103 k€" fails. Suffixes `_eur`, `_eur_m`, `_pct`, "(k€)" work. | Brasa | False UNSUPPORTED_NUMBER; the workaround is renaming the column. |
| F5 | Formulas have no unit conversion (EUR vs EUR_K). | tiendas | The agent must cite a fact already in the right unit. |
| F6 | Numbers written in words ("dos paradas", "seis meses") are not extracted. | packaging, Contabilia | They cannot be cited. |
| F7 | Table cells are compared unit-free: "10 M€" against a k€ column needs a computed fact. | tiendas | An extra step for the agent. |

## Locale and rendering

| # | debt | effect |
|---|---|---|
| L1 | **No locale number formatting.** `meta.language: "es"` does not change number formats: tables print 1,066 / 2.67x, and LibreOffice chart labels print "20.5". | Agents pre-format numbers as text cells (losing number alignment), or use `thousands: false`. |
| L2 | `delta_colors: "muted"` + `highlight` paints a highlighted loss in the accent colour (green). | A loss can read as good news. The highlight colour should follow the sign, or be neutral-dark. |
| L3 | A header in a `kind: "text"` column is always left-aligned, even with `align: "right"`. | Misaligned headers. |
| L4 | STORY_GT_LONG fires below its documented 35-word threshold (observed at 34). | A spurious warning. |
| L5 | KPIs + commentary (no exhibit) and KPIs + process diagram have no layout (LAYOUT_NONE). | Slides are rebuilt around another exhibit. |
| L6 | No cause → effect exhibit; no decisions-table + timeline combination; no explicit n/a cell in grouped categories. | A process chart reads as steps, and gate dates sit in a table. |
| L7 | No "km" unit. Spanish m² reads as PLAIN_M. | Units are lost in extraction. |

## Evidence

| # | debt | status |
|---|---|---|
| E1 | Human evidence is one expert rater (owner decision), and every round is small. s2: 3–1 for the protocol. s3: 1–0. s4: 1–4 against protocol 1.3, which is what led to 1.4. Brasa (1.4): accepted as perfect. | Protocol 1.4 has not been through a blind multi-case round; the owner accepted it on one real case. |
| E2 | External slide holdout and unseen corporate template (from v1.6) | awaiting external input |
| E3 | The development cases (sets 01 and 02) and their references were written by the developing agent; packaging C3 was wrong and is marked contested. | development data only |

## Status after 1.7.1 (fine-tuning pass, 2026-10-02)

No new agent runs were made. Each fix is covered by a test. The stored decks were the regression set: the
SaaS deck, the tiendas deck, the real Brasa deck (private) and the v1.7 development run. All four still
pass the reasoning check with 0 hard failures. Brasa re-renders at 98.1 with Spanish number formats.

| # | status | what changed |
|---|---|---|
| F1 | **fixed** (residual noted) | Table cells and chart values must BE a cited fact value, in any scale (×10³, ×10⁶), within display rounding; derived cells are written as computed facts. On the Brasa deck, 4 of 5 injected invented values are now blocked. **Residual:** a value that is a real fact cited on the same slide but placed in the wrong cell is not caught; that needs cell-to-fact binding (v1.8). |
| F2 | **fixed** | Prose-vs-prose money conflicts with no period (shared measure word and a shared two-word phrase, different files, >10% apart). It finds the real almacén closure-cost conflict and the Seguros Alba cost conflict, with no false positives on the development or external cases. |
| F3 | **fixed** | Numbers inside text cells of report tables become prose facts located at their cell ("… r2c2"). |
| F4 | **fixed** | `_k` / `_m` header suffixes: EUR_K / EUR_M when the column is money (cost, sales, EBITDA, rent …), PLAIN_K otherwise. |
| F5 | **fixed** | `to(F0212, "EUR_K")` converts a fact's unit inside a formula; conversion across kinds is refused. |
| F6 | **closed by design** | Since protocol 1.4, small whole counts are not checked, so number words need no citation. |
| F7 | **fixed** | Cells written in another scale of the same quantity ground (10 M€ against 10.000 k€). |
| L1 | **fixed** | `meta.language` "es" (or fr/de/it/pt/nl) formats every number in tables and overlays as 1.066,5 / 2,67x. Native chart labels carry the locale tag `[$-C0A]`, so LibreOffice and PowerPoint print "20,5". |
| L2 | **fixed** | A highlighted loss in a waterfall uses the negative colour, never the accent. |
| L3 | **fixed** | An explicit `align` on a text column is honoured in the header. |
| L4 | **fixed** | The STORY_GT_LONG word count counts words as a reader does. |
| L5 | **fixed** | New layout `kpi_grid_commentary` (KPIs + commentary, no exhibit). The KPI strip layouts accept process / flow exhibits. A process step written with `label` no longer crashes the build. |
| L6 | **moved to v1.8 (features)** | A cause → effect exhibit, a decisions table + timeline, explicit n/a cells. |
| L7 | **fixed** | km and m² units in headers and prose. |
| E1–E3 | open | Evidence debts are unchanged: one rater, protocol 1.4 accepted on one real case, external slide holdout and template pending. |
