# Editorial Logic Layer (v3.1)

The engine already owned what a slide shows and how it is drawn. From v3.1 it also owns **how the
slide's message is worded**: every substantive slide states an evidence-backed takeaway, and messages
that sit at the same logical level are written as one family. Specification: `docs/V31_SPEC.md`.

```
storyline → slide intent → PROPOSITION → ACTION TITLE ENGINE → PARALLEL WORDING GUARANTEE → EDITORIAL QA
          → [compose] → plan (visual + layout + density) → PPTX → render → visual QA
```

The layer runs **before** composition and planning (`pipeline.run`), so layout candidates are scored on
the final headline and every candidate gets the same wording. The planner still lints every headline
on its own (defence in depth). Nothing here needs a language model: candidate wording comes from the
reasoning agent; acceptance, rejection and selection are deterministic.

## Three objects, never interchangeable

| object | field | example |
|---|---|---|
| purpose | `purpose` | Show why gross margin declined |
| proposition | `proposition` | `{"statement": "The shift toward electronics explains most of the gross-margin decline", "role": "diagnosis", "claim_type": "driver", "evidence_ids": ["F18"], …}` |
| headline | `headline` (+ optional `headline_candidates`) | Electronics mix explains most of the 1.9 pp gross-margin decline |

`deck.json` stays the only source of truth: `proposition`, `headline_candidates`, `story_role`,
`editorial.parallel_group` / `parallel_group` are new optional fields of the same spec
(`docs/SPEC_REFERENCE.md`). The compiler adds diagnostic `_editorial` metadata to each slide of the
resolved spec; it is stripped from any spec the engine writes back (`deck.autofixed.json`).

## Modes (`meta.editorial_mode`)

| mode | proposition | hard findings | rewrites |
|---|---|---|---|
| `mbb_strict` | required on every content / exec-summary / statement slide | **errors**: the deck fails | candidate selection; safe deterministic rewrite |
| `standard` (default when the spec says nothing) | inferred from the headline if absent (marked, never accepted by strict) | warnings | as strict |
| `legacy` | inferred | info only | none |

`cpe scaffold` writes `mbb_strict` into every new deck, and the three example decks are strict. Old
specs keep working unchanged in `standard`.

Exempt kinds (title-style labels allowed): `cover`, `divider`, `agenda`, `appendix_divider`, `closing`.

## What it checks

- **Action titles** (`docs/ACTION_TITLE_ENGINE.md`): the headline is a conclusion, not a topic or the
  slide's purpose; one governing message; every number is in the evidence or derivable from it at the
  precision written; no drift from the proposition in direction, magnitude, entity, scope, period,
  confidence, causal strength, recommendation or decision; the deck's language.
- **Parallel wording** (`docs/PARALLEL_WORDING.md`): explicit groups and structural sibling groups
  (process steps, roadmap workstreams, recommendation cards, options, comparison criteria, design
  principles, executive-summary statements, key-line arguments) share one grammatical family, tense,
  voice, granularity, punctuation and capitalisation.
- **Horizontal logic**: the governing thought and key-line points are arguments, the executive summary
  holds conclusions (not an agenda), every content slide proves a key-line point, every key-line point
  is proved, and the **headline strip** answers what happened · why · so what · what next · what
  decision. Page-turn regressions are advisory.

Truth outranks symmetry: the guarantee reports and asks for rewrites; it never rewrites a member to make
a group look parallel, and the safe rewrite never papers over a headline that contradicts its
proposition (that disagreement belongs upstream).

## Verdicts and artifacts

Every `cpe run` writes, beside `qa_report.*`:

| file | content |
|---|---|
| `editorial_report.json` / `.md` | Editorial QA verdict; per slide: proposition, candidates, selected title, score, findings; groups; horizontal logic |
| `headline_strip.md` | the titles alone and the five questions they answer |
| `editorial_ghost_deck.md` | the ghost deck with role, signature, ATE score and parallel status per title |
| `ghost_deck.md` | unchanged |

`qa_report` reports five separate verdicts — **Factual, Editorial, Visual, Authoring, Brand** — and the
deck passes only if all pass. There is no composite score: a visually perfect slide with a false
headline fails, and so does a true headline on a broken slide. In strict mode a failing deck is still
built and rendered for inspection; it is never reported as passed.

Post-render, the rendered line count is the truth for title fit: a title still over two lines raises
`EDITORIAL_HEADLINE_FIT` (compress through the ATE with a new candidate). Visual autofix never edits
`headline`, `text`, `headline_candidates` or `proposition`; a layout step that changes compiled wording
is reverted (`EDITORIAL_WORDING_RESTORED`).

## Commands

```
cpe editorial check deck.json [-o dir] [--mode …]     # editorial QA → editorial_report.md (exit 1 if failed)
cpe editorial explain deck.json                        # per slide: proposition, candidates, selection, findings
cpe editorial ghost deck.json [-o dir]                 # headline_strip.md + editorial_ghost_deck.md
cpe editorial normalize old.json -o deck.editorial.json   # legacy spec → provisional propositions to confirm
cpe editorial eval --set dev|holdout [--record]        # the editorial fixtures (evals/editorial)
cpe run deck.json --editorial-mode mbb_strict          # override the spec's mode for one run
cpe update OLD.pptx SOURCES -o WORK --normalize-editorial
cpe human build-editorial --pairs pairs.json -o round  # blind A/B of headline wordings / headline strips
```

## Updating an existing deck

`reasoning/messages.py` still answers *does the old argument hold with the new numbers?*. When it no
longer holds, its mechanical proposal becomes a **revised proposition** and goes through the ATE with
any wording the agent adds to the edit's `candidates`; the `set_headline` edit records the proposition
and the ATE verdict and stays `approved: false` until a person approves it. A headline that holds is
preserved. With `--normalize-editorial`, titles that hold but are not action titles are flagged
(`needs_wording` until a candidate passes; an unworded edit is never applied). A rebuilt slide carries
its revised proposition and its numbers as evidence and is compiled in `mbb_strict`, like a new slide.

## Limits (measured, not assumed)

The checks are lexical and structural, in English and Spanish. They catch the failure classes of the
spec (§91) on the fixtures in `evals/editorial`, but they do not understand the business: a proposition
that is itself wrong passes if the headline states it faithfully, entity drift is caught when the
entities are labelled in the evidence or the exhibit, and an unknown verb form can make a conclusion
look like a label (the lint then asks for a verb). Results per release are in `docs/V31_STATUS.md`.
