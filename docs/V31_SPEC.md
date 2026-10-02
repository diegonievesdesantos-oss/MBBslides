# MBBslides v3.1 — Editorial Logic Layer

**Action Title Engine + Parallel Wording Guarantee**

- Status: mandatory product capability
- Proposed release: `v3.1.0`
- Purpose: close the remaining editorial gap between a technically correct consulting deck and an MBB-grade consulting deck.

> This is the owner's specification, saved as given. What was actually built and measured is in
> `docs/V31_STATUS.md`; the user-facing description is in `docs/EDITORIAL_LAYER.md`.

## 1. Executive decision

MBBslides currently has:

- source ingestion;
- traceable fact model;
- analysis;
- hypothesis / insight reasoning;
- storyline generation;
- Pyramid Principle structure;
- slide intent;
- visual reasoning;
- native editable PPTX generation;
- layout intelligence;
- content-density management;
- corporate template ingestion;
- visual QA;
- render-based QA;
- regression evaluation;
- reproducibility;
- headline linting.

However, the current architecture still assumes that the final wording of the slide message has already been written correctly upstream.

That is the remaining gap.

The existing headline engine can detect many bad headlines, but it does not own their generation. In other words:

```
today

reasoning
    ↓
storyline
    ↓
someone writes headline
    ↓
headline lint
    ↓
visual planning
```

The target architecture must become:

```
reasoning
    ↓
storyline
    ↓
SLIDE PROPOSITION
    ↓
ACTION TITLE ENGINE
    ↓
PARALLEL WORDING GUARANTEE
    ↓
EDITORIAL QA
    ↓
visual reasoning
    ↓
layout / composition
    ↓
PPTX
    ↓
render
    ↓
visual QA
```

The essential principle is:

> The engine must own not only what the slide means, but also the form in which that meaning is expressed.

A slide should not reach visual planning unless its editorial contract is already valid.

## 2. Why these capabilities belong in the core

These are not cosmetic capabilities. They represent two different dimensions of consulting communication.

### 2.1 Action Title Engine = vertical logic

For every slide:

> What is the single conclusion the audience should take away from this page?

The action title must express that conclusion. The body of the slide then proves it.

Conceptually:

```
ACTION TITLE
      ↓
claim made by the slide
      ↓
exhibit / analysis / evidence
      ↓
proof of that claim
```

This is vertical logic.

A headline such as `Revenue evolution` does not make a claim. It only names a subject.

A headline such as `Revenue grew 12% in 2026, driven primarily by enterprise customers` contains a conclusion that the exhibit can prove.

The difference is structural, not stylistic.

### 2.2 Parallel Wording Guarantee = horizontal editorial consistency

For a set of comparable messages:

> Are equivalent ideas expressed using equivalent grammatical structures?

For example:

Bad:

```
1. Procurement fragmentation
2. Finance has too many manual activities
3. Improving pricing discipline
```

The ideas may be valid, but they are not expressed as one logical family.

Better:

```
1. Consolidate procurement to reduce supplier fragmentation
2. Automate finance workflows to remove manual rework
3. Tighten pricing discipline to protect margin
```

The pattern is now `VERB + OBJECT + BUSINESS OUTCOME`. The reader understands the hierarchy immediately.

This applies not only to slide titles. It applies to:

- key-line arguments;
- executive-summary messages;
- recommendation pillars;
- process steps;
- roadmap workstreams;
- comparison dimensions;
- options;
- initiative names;
- section summaries;
- repeated cards;
- sibling labels;
- slide sequences where the messages belong to the same logical family.

## 3. Important definition: "Action title" does not mean "imperative"

The term must not be interpreted as: *every slide title must tell the client to do something.* That would be wrong.

An action title is a takeaway sentence, not necessarily an instruction.

| Kind | Example |
|---|---|
| Observation | Premium customers generate 2.3× the contribution margin of standard customers |
| Diagnosis | Three low-performing regions account for 72% of the EBITDA gap |
| Causal conclusion | Lower conversion, rather than traffic, explains most of the revenue shortfall |
| Implication | Without pricing action, margin will remain below the 2027 target |
| Recommendation | Reprice electronics first to recover the majority of the margin gap |
| Decision | Approving the two priority initiatives unlocks €14m of annual EBITDA |

All are valid action titles. The common property is: **they state what the slide means.**

## 4. Architectural principle

Do not implement Action Title Engine as a collection of headline templates applied to raw slide text.

The correct architecture is:

```
facts
  ↓
analysis
  ↓
insight
  ↓
storyline role
  ↓
SLIDE PROPOSITION
  ↓
linguistic realization
```

The semantic statement and its linguistic rendering must be separated. This gives us:

```
WHAT WE MEAN
≠
HOW WE SAY IT
```

The first must remain stable. The second can be rewritten until it reaches consulting quality.

## 5. New core object: Slide Proposition

Introduce a first-class `proposition` object for every substantive slide. The proposition is the semantic contract of the slide.

```json
{
  "proposition": {
    "statement": "The gross-margin decline is primarily explained by the increase in electronics mix",
    "role": "diagnosis",
    "claim_type": "driver",
    "subject": "gross margin",
    "direction": "decline",
    "driver": "electronics mix",
    "implication": "electronics should be the first recovery lever",
    "timeframe": "2026",
    "evidence_ids": ["F014", "A006"],
    "confidence": "high"
  }
}
```

The final headline could then be:

```
Electronics mix explains most of the gross-margin decline, making it the first recovery lever
```

The key point is that rewriting this headline must never change the proposition.

## 6. Proposition contract

A proposition should support the following fields. Not every field is mandatory.

```json
{
  "statement": "...",
  "role": "...",
  "claim_type": "...",
  "subject": "...",
  "predicate": "...",
  "direction": "...",
  "magnitude": null,
  "comparison": null,
  "driver": null,
  "implication": null,
  "recommended_action": null,
  "decision": null,
  "timeframe": null,
  "scope": null,
  "qualifiers": [],
  "evidence_ids": [],
  "analysis_ids": [],
  "confidence": "high"
}
```

Possible `role` values: `context`, `observation`, `diagnosis`, `driver`, `comparison`, `insight`, `implication`, `recommendation`, `decision`, `risk`, `status`, `impact`, `implementation`.

Possible `claim_type` values: `fact`, `trend`, `comparison`, `composition`, `driver`, `causal`, `constraint`, `risk`, `opportunity`, `recommendation`, `decision`, `impact`, `status`.

## 7. Proposition generation

The proposition belongs immediately after slide intent.

Current conceptual flow: storyline → slide purpose → message type → evidence.

Target: storyline → slide purpose → message role → evidence → **PROPOSITION**.

The proposition should answer:

1. What exactly are we asserting?
2. About what subject?
3. In which direction?
4. Relative to what?
5. Over what period?
6. With what implication?
7. What evidence proves it?
8. How certain are we?

Only after these questions are resolved should wording begin.

## 8. Action Title Engine

Create:

```
src/cpe/editorial/
    __init__.py
    compiler.py
    action_titles.py
    parallel.py
    proposition.py
    qa.py
    signatures.py
    report.py
```

The main API should look conceptually like `compile_editorial(spec, profile)` and return `compiled_spec, editorial_report`.

## 9. Responsibilities of Action Title Engine

The ATE has five responsibilities:

1. understand the proposition
2. determine the correct headline form
3. produce / accept candidate wording
4. prove that wording has not changed the proposition
5. reject the slide if no acceptable action title exists

The last point matters. The engine should be fail-closed. It is preferable to return `EDITORIAL_HEADLINE_UNRESOLVED` than to allow `Market overview` through the pipeline.

## 10. Headline generation architecture

Do not introduce an arbitrary external LLM dependency into the rendering library.

Separate *semantic candidate generation* from *deterministic acceptance*.

The upstream reasoning agent can generate one or several candidate headlines:

```json
{ "headline_candidates": ["...", "...", "..."] }
```

The Action Title Engine owns: validation; scoring; selection; safe normalization; diagnostics; rejection.

If the existing agent produces a bad headline (`Margin evolution`), ATE should return something like:

```
REJECTED
HEADLINE_TOPIC
Missing conclusion
Expected proposition:
"Electronics mix explains the majority of the gross-margin decline"
```

The agent can then regenerate. This architecture avoids turning the Python engine into a poor natural-language generator while still guaranteeing that bad wording never reaches the final deck.

## 11. Deterministic fallback

ATE should nevertheless support deterministic transformations when semantics make the rewrite unambiguous.

Example: `Revenue decline` with proposition `{"subject": "revenue", "direction": "decline", "magnitude": "8%", "timeframe": "2026"}`. Safe fallback: `Revenue declined 8% in 2026`.

But ATE must not invent `Revenue declined 8% because customer demand weakened` unless the causal driver is explicitly supported by the proposition/evidence.

## 12. Action-title taxonomy

The engine should classify the intended headline before evaluating wording.

| # | Type | Pattern | Example |
|---|---|---|---|
| 12.1 | Factual conclusion | SUBJECT + CHANGE / STATE + MAGNITUDE | EBITDA increased 14% despite flat revenue |
| 12.2 | Comparative conclusion | A + OUTPERFORMS / LAGS + B + RELEVANT DIFFERENCE | Enterprise customers generate 2.3× more contribution than SMB customers |
| 12.3 | Driver conclusion | DRIVER + EXPLAINS / ACCOUNTS FOR + OUTCOME | Three regions explain 72% of the profitability gap |
| 12.4 | Causal conclusion | CAUSE + DRIVES + EFFECT | (requires stronger evidence than correlation) |
| 12.5 | Implication | FACT / DIAGNOSIS + IMPLIES + BUSINESS CONSEQUENCE | Current capacity will constrain growth from Q3 unless a second line is added |
| 12.6 | Recommendation | ACTION + OBJECT + BUSINESS OUTCOME | Prioritise electronics repricing to recover most of the margin gap |
| 12.7 | Decision | DECISION + UNLOCKS / PROTECTS / REQUIRES + OUTCOME | Approving wave 1 now protects the Q2 implementation window |
| 12.8 | Risk | CONDITION + PUTS + VALUE / TARGET + AT RISK | A six-week delay would put the 2027 savings target at risk |
| 12.9 | Status | PROGRAM / KPI + IS ON / OFF TRACK + REASON | The programme remains on track despite a two-week delay in workstream 3 |

For 12.4 the engine must distinguish `is associated with` from `causes` or `drives`. Unsupported causal language should be a hard editorial error.

## 13. Headline quality dimensions

Every candidate should be assessed independently across the following dimensions.

- **Proposition fidelity** — does the headline express the proposition without changing it? Mandatory.
- **Evidence support** — can the evidence on the slide or elsewhere in the deck support the claim? Mandatory.
- **Answer-first structure** — does the reader receive the answer rather than the subject? Bad: `Analysis of channel performance`. Good: `Digital channels now generate over half of incremental sales`.
- **So-what** — does the headline communicate why the information matters? Not every slide requires an explicit business implication, but the engine should prefer it when supported.
- **Specificity** — prefer `Three plants account for 80% of downtime` over `Downtime is concentrated in a few plants` when the numbers are supported.
- **One-message discipline** — a headline should express one governing idea. Bad: `Revenue grew 12% and margins fell 3 pp and costs remain above plan` (three messages).
- **Concision** — the title should contain only the claim required to understand the page.
- **Sentence completeness** — content-slide action titles should normally contain a verb.
- **Directionality** — prefer `Margins fell 1.9 pp` to `Margin performance`.
- **Business language** — avoid unnecessary prose and filler.

## 14. Hard Action Title gates

These should be errors in `mbb_strict` mode:

```
HEADLINE_MISSING
HEADLINE_PLACEHOLDER
HEADLINE_TOPIC
HEADLINE_PROPOSITION_MISMATCH
HEADLINE_NUMBER_UNSUPPORTED
HEADLINE_CAUSALITY_UNSUPPORTED
HEADLINE_COMPARISON_UNSUPPORTED
HEADLINE_DIRECTION_MISMATCH
HEADLINE_TIMEFRAME_MISMATCH
HEADLINE_TWO_GOVERNING_MESSAGES
HEADLINE_UNRESOLVED
```

A deck with one of these unresolved should not receive `EDITORIAL QA: PASSED`.

## 15. Soft Action Title signals

Warnings or advisory signals:

```
HEADLINE_LONG
HEADLINE_WEAK_VERB
HEADLINE_VAGUE
HEADLINE_REDUNDANT
HEADLINE_REPEATED_OPENING
HEADLINE_QUESTION
HEADLINE_TITLE_CASE
HEADLINE_LOW_INFORMATION
HEADLINE_SO_WHAT_WEAK
```

Some of these already exist in `core/headline.py`. Do not duplicate them. Refactor so the new layer extends the existing engine.

## 16. Existing `core/headline.py`

Do not delete it. It already contains useful deterministic checks such as `HEADLINE_TOPIC`, `HEADLINE_TWO_MESSAGES`, `HEADLINE_VAGUE`, `HEADLINE_LONG`, `HEADLINE_UNQUANTIFIED`, `HEADLINE_NUMBER_UNSUPPORTED`.

It should become a component of the new ATE:

```
ATE
 ├── proposition validator
 ├── candidate generator / receiver
 ├── semantic fidelity checker
 ├── existing headline lint
 └── candidate selector
```

This is an evolution of the existing architecture, not a replacement.

## 17. Headline scoring

Maintain a separate editorial score. Do not merge it into visual composition.

Suggested diagnostic score:

```
Proposition fidelity        25
Evidence support            25
Answer-first / conclusion   15
Specificity                 10
So-what                     10
Sentence structure           5
Concision / fit              5
Wording hygiene              5
                           ----
                            100
```

However: a score must never override a hard semantic failure. For example `90/100` with unsupported causality still means `FAIL`.

## 18. Why editorial score must stay separate

Current evaluation correctly separates several quality signals. Continue that architecture.

Do not create `final quality = 50% visual + 50% editorial`, because a visually perfect but semantically false slide must fail. Likewise, a semantically perfect but visually broken slide must fail.

Report Factual QA, Editorial QA, Visual QA, Composition and Brand fidelity as separate dimensions.

## 19. Parallel Wording Guarantee

Create `src/cpe/editorial/parallel.py`.

The purpose is not to make every title in a deck grammatically identical. That would make the deck robotic. The purpose is:

> Elements that represent the same logical category must use the same linguistic architecture.

## 20. What should be parallelised

Parallelism should be mandatory for genuine sibling elements.

**Deck-level groups** — storyline key lines; recommendation pillars; strategic options; problem drivers; value-creation levers; risks; workstreams.

**Slide-level groups** — executive-summary statements; cards; process steps; roadmap workstreams; initiative rows; option headers; comparison criteria; operating-model pillars; design principles; list of recommendations.

**Headlines** — headlines should only be grouped when they genuinely belong to the same rhetorical family. For example, three diagnosis slides within one MECE driver decomposition may appropriately use `X explains... / Y explains... / Z explains...`. But an entire 20-slide deck should not be forced into one structure.

## 21. Explicit parallel groups

Support an explicit authoring contract:

```json
{ "parallel_group": "recommendation_pillars", "parallel_role": "recommendation" }
```

At storyline level:

```json
{ "id": "K2", "role": "recommendation", "message": "...", "parallel_group": "key_line_recommendations" }
```

At repeated-element level:

```json
{ "items": [ { "label": "...", "parallel_group": "initiative_names" } ] }
```

## 22. Automatically detected parallel groups

Automatic grouping should be conservative. Do not parallelise content merely because it appears next to each other.

Automatically group when structure provides strong evidence: process steps, roadmap workstreams, recommendation cards, option columns, executive-summary bullets, key-line siblings, comparison pillars, design principles, initiative lists.

For slide headlines, auto-group only if they are: consecutive or sibling slides; under the same storyline node; of the same message role; and logically comparable.

## 23. Wording signatures

Represent grammar as a lightweight structural signature:

```
CLAUSE_SUBJECT_VERB_OUTCOME
VERB_OBJECT_OUTCOME
SUBJECT_CHANGE_MAGNITUDE
DRIVER_EXPLAINS_OUTCOME
CONDITION_IMPLIES_CONSEQUENCE
ACTION_TO_OUTCOME
NOUN_PHRASE
```

`Reduce procurement fragmentation by consolidating the supplier base` → `VERB_OBJECT_OUTCOME`.
`Automate finance workflows to reduce manual rework` → `VERB_OBJECT_OUTCOME`. These are parallel.

## 24. Parallel group contract

```json
{
  "id": "recommendation_pillars",
  "members": ["s12.pillar1", "s12.pillar2", "s12.pillar3"],
  "semantic_role": "recommendation",
  "target_signature": "VERB_OBJECT_OUTCOME",
  "voice": "active",
  "tense": "imperative",
  "capitalization": "sentence",
  "max_length_spread": 0.35
}
```

## 25. Parallel Wording Guarantee checks

For each group test: same semantic role; compatible grammatical signature; same voice where relevant; same tense where relevant; same level of abstraction; same semantic granularity; consistent capitalization; consistent punctuation; similar information density; consistent use of numbers; consistent use of qualifiers.

## 26. Semantic granularity matters

Parallel wording is not just grammar. Bad:

```
Reduce supplier fragmentation
Automate finance
Increase EBITDA by €12m through pricing
```

The first is an operational action. The second is extremely broad. The third mixes action and quantified outcome. Even if all start with verbs, they are not truly parallel. The guarantee therefore needs to compare semantic granularity as well as syntax.

## 27. Preserve meaning above symmetry

Never rewrite a statement merely to make it look more parallel if the result changes its meaning.

Priority order:

1. factual truth
2. proposition fidelity
3. logical structure
4. parallel wording
5. stylistic elegance

Parallelism must never outrank truth.

## 28. Parallelism failure modes

```
PARALLEL_SIGNATURE_MISMATCH
PARALLEL_ROLE_MISMATCH
PARALLEL_TENSE_MISMATCH
PARALLEL_VOICE_MISMATCH
PARALLEL_GRANULARITY_MISMATCH
PARALLEL_LENGTH_OUTLIER
PARALLEL_PUNCTUATION_MISMATCH
PARALLEL_NUMBERING_MISMATCH
```

For explicit mandatory groups `PARALLEL_SIGNATURE_MISMATCH` should be an editorial error. For automatically inferred low-confidence groups it can remain a warning.

## 29. Horizontal logic and parallel wording are different

Horizontal logic asks: *If I read only the slide headlines, do I understand the argument?*

Parallel wording asks: *Where several messages occupy the same logical level, are they written as members of the same family?*

Both are required.

## 30. Extend the existing ghost deck

The existing `ghost_deck.md` is the natural artifact for this. Create additionally `editorial_ghost_deck.md`:

```
# Ghost deck

## Governing thought
Repricing electronics can recover most of the 2027 margin gap

### DIAGNOSIS
01. Gross margin fell 1.9 pp as electronics increased its share of sales
02. Electronics explains the majority of the mix-driven margin dilution
03. Freight and store labour contributed only marginally to the decline

### RECOMMENDATION
04. Reprice electronics first to recover ~1.4 pp
05. Make future electronics growth conditional on margin
06. Protect store labour while monitoring freight productivity

### IMPACT
07. The programme recovers most of the gap without reducing store capacity
```

Below each title optionally show:

```
role: diagnosis
signature: SUBJECT_VERB_OUTCOME
ATE: 93
parallel group: diagnosis_drivers
parallel: PASS
```

## 31. Add a "headline strip test"

The engine should perform a deck-level test using only the action titles. The strip should answer:

> Can a senior executive understand what happened; why; what it means; what should happen next; and what decision is required — without reading the slide bodies?

This should be an explicit editorial artifact: `headline_strip.md`.

## 32. Storyline integration

Current storyline structure is approximately governing_thought → key_line → slides. Keep it. Extend to:

```
governing_thought
    ↓
key_line
    ↓
slide purpose
    ↓
slide proposition
    ↓
action title
```

Every content slide must prove either a key-line message, or a subordinate proposition necessary to prove it.

## 33. Key-line wording

The `key_line` itself should also receive editorial treatment. The current architecture already requires key-line elements to represent arguments of the same logical type. The new layer should additionally make their wording parallel when appropriate.

Bad:

```
K1: Margin decline
K2: Electronics has become a problem
K3: We recommend repricing
```

Better:

```
K1: Electronics mix explains most of the margin decline
K2: Current growth plans would deepen the margin gap
K3: Repricing electronics can recover most of the lost margin
```

The progression is logically explicit.

## 34. Executive-summary integration

Executive summaries require especially strict wording. Every statement should be answer-first, self-contained, evidence-backed, and parallel to its siblings where logically equivalent.

An executive summary should never become `Market / Financial performance / Operational considerations / Recommendation`. That is an agenda. It must contain conclusions.

## 35. Visual reasoning must happen after editorial compilation

This ordering is mandatory. Do not do visual selection → headline rewrite, because headline length and semantic structure affect layout choice, title height, exhibit emphasis, density, proof selection, chart annotation and focal point.

Correct: proposition → final headline → visual encoding → layout.

## 36. Exact integration into `pipeline.py`

The current high-level execution does: optional compose → plan() → build → render → QA → autofix.

Change it conceptually to:

```
current = spec

current, editorial_report = editorial.compile(current)

if compose:
    current, decisions = compose(current)

resolved, content_issues = plan(current)

build(...)
render(...)
QA(...)
```

ATE must therefore run before `compose()` and before `plan()` — because candidate layout selection must evaluate the final headline, not a temporary one.

## 37. Keep planner headline linting

Even after ATE exists, keep `lint_headline(...)` in `planner.py` as defense in depth:

```
ATE writes / accepts headline
        ↓
Editorial QA certifies headline
        ↓
Planner independently lints headline
```

Never remove the second check merely because the first exists.

## 38. Planner integration

`planner.py` should receive a spec where every strict content slide already contains:

```json
{ "proposition": {...}, "headline": "...", "_editorial": { "status": "passed" } }
```

If not, `EDITORIAL_NOT_COMPILED` should be returned in strict mode.

## 39. `deck.json` remains the source of truth

Do not create a second competing slide specification. Extend `deck.json`:

```json
{
  "id": "s07",
  "kind": "content",
  "section": "K2",
  "purpose": "Explain the main driver of the margin decline",
  "message_type": "change_bridge",
  "proposition": {
    "statement": "Electronics mix explains most of the gross-margin decline",
    "role": "diagnosis",
    "claim_type": "driver",
    "subject": "gross margin",
    "driver": "electronics mix",
    "evidence_ids": ["F18", "A05"],
    "confidence": "high"
  },
  "headline": "Electronics mix explains most of the gross-margin decline",
  "editorial": {
    "headline_type": "driver",
    "parallel_group": "margin_diagnosis",
    "signature": "DRIVER_EXPLAINS_OUTCOME"
  },
  "visual": { "type": "waterfall" }
}
```

## 40. `_editorial` resolved metadata

The resolved spec can add:

```json
{
  "_editorial": {
    "compiled": true,
    "headline_score": 96,
    "headline_type": "driver",
    "signature": "DRIVER_EXPLAINS_OUTCOME",
    "parallel_group": "margin_diagnosis",
    "parallel_status": "passed",
    "proposition_fidelity": "passed",
    "evidence_support": "passed",
    "candidate_count": 3,
    "selected_candidate": 2,
    "reasons": []
  }
}
```

This should be diagnostic metadata. It must not contaminate the authoring contract unnecessarily.

## 41. Cover, divider and agenda exceptions

Not every page requires an action title. Explicit exemptions: cover, divider, agenda, appendix divider, closing / contact. These can have title-style labels.

However exec_summary, content, decision, recommendation and analysis slides must use action-title logic. This distinction should be explicit in code.

## 42. Action Title Engine and source lineage

Every quantitative statement in a headline remains subject to existing lineage rules. ATE cannot invent a number because it makes a better title.

Proposition `Margin declined materially`, evidence `margin: 18.2% → 16.3%`: ATE may derive `Margin fell 1.9 pp` only if `1.9 pp` is derivable under the existing arithmetic lineage rules. The derivation should be recorded.

## 43. Causal language protection

This needs a dedicated check. Words such as *drives, causes, explains, results from, due to, because, provoca, causa, explica, se debe a, impulsa* should require an appropriate proposition/evidence type.

If evidence only shows correlation, safer wording should be used: *coincides with, is associated with, is concentrated in, alongside*.

Do not create stronger causal inference through copywriting.

## 44. Recommendation protection

A recommendation headline must be connected to a recommendation proposition. Do not transform `Option A has the highest NPV` into `Choose Option A` unless the reasoning layer has concluded that Option A should be recommended.

Best option on one metric ≠ final recommendation.

## 45. Comparison protection

Words like *best, worst, highest, lowest, leading, largest, most attractive* need proof across the comparison universe available on the slide. Reuse existing comparison/superlative logic wherever possible.

## 46. Action title fitting

Do not use a fixed character count as the definitive rule. Actual rendered width matters. Use profile headline font, available title box width, font metrics and brand template geometry.

Goals: 1 line preferred; 2 lines acceptable; 3 lines generally rejected. But an exact line count should ultimately be verified after render because LibreOffice/PowerPoint line breaking is the ground truth.

## 47. Editorial QA before rendering

Introduce `editorial_report.json` and `editorial_report.md`. Possible summary:

```
Editorial QA: PASSED

Action titles
-------------
slides checked: 18
passed: 18
hard errors: 0
warnings: 3
mean diagnostic score: 93.8

Parallel wording
----------------
groups checked: 7
mandatory groups passed: 7 / 7
warnings: 1

Horizontal logic
----------------
ghost deck: passed
orphan propositions: 0
unsupported key-line points: 0
```

## 48. Editorial QA after rendering

Some headline checks cannot be trusted until render. Continue checking `HEADLINE_LINES`, `HEADLINE_WIDOW`, overflow and collision.

Editorial QA and visual QA therefore cooperate: semantic/editorial QA → render → typographic headline QA.

## 49. Update workflow integration

This capability must work for both new deck generation and existing deck update, but behavior should differ.

## 50. Existing `reasoning/messages.py`

Today this module determines whether a headline still holds; substitutes updated numbers; detects broken thresholds; handles signs; handles ordering; handles superlatives; produces a mechanical proposal.

Keep all that reasoning. It is valuable. But its proposal should become semantic input to ATE, not necessarily the final wording.

New flow:

```
old headline
    ↓
messages.review()
    ↓
headline still holds?
    │
    ├── yes → preserve by default
    │
    └── no
         ↓
revised proposition
         ↓
ATE
         ↓
new headline proposal
         ↓
human approval
```

## 51. Why not simply replace `messages.py`

Because `messages.py` answers an important question: *Does the old argument still hold after the numbers changed?* ATE answers a different question: *Given the argument that is now true, what is the correct action title?* Keep those responsibilities separate.

## 52. `headline_edits()`

Today this ultimately creates `set_headline` proposals. Change its role conceptually from `mechanical rewrite → set_headline` to `mechanical semantic update → new proposition → ATE → set_headline proposal`. Still `approved = false` by default.

Never silently rewrite an existing client's slide title.

## 53. Existing-deck preservation

For `cpe update`, preserve existing valid headlines unless:

1. the underlying proposition no longer holds;
2. the slide is rebuilt;
3. the user explicitly asks for editorial normalization.

Add an optional mode `cpe update ... --normalize-editorial`. In that mode, topic titles or non-MBB wording can be rewritten even when the underlying numbers have not changed. Default update mode should remain conservative.

## 54. Rebuild integration

Current rebuild uses old slide + approved numbers + proposed headline and creates a new slide spec. Change to: old slide + approved numbers + new proposition + ATE headline + parallel context, before `pipeline.run()`.

A rebuilt slide must comply with the same editorial rules as a new slide.

## 55. New-deck generation

For newly generated decks there should be no compatibility escape. In `mbb_strict` mode:

```
content slide without proposition → error
content slide without action title → error
mandatory parallel group mismatch → error
unsupported headline claim → error
```

## 56. Add editorial mode to metadata

```json
{ "meta": { "editorial_mode": "mbb_strict" } }
```

Modes:

- `mbb_strict` — mandatory ATE + PWG.
- `standard` — editorial issues may remain warnings.
- `legacy` — primarily used for ingesting existing material without rewriting it.

For MBBslides-generated decks, default should be `mbb_strict`.

## 57. Parallel Wording at executive-summary level

Bad:

```
Margins fell sharply
Electronics is the main issue
Need to take pricing action
```

Possible normalized set:

```
Electronics mix drove most of the 1.9 pp margin decline
Current growth plans would widen the margin gap further
Repricing electronics can recover ~1.4 pp in 2027
```

These are not mechanically identical. Parallelism here means complete declarative conclusions, similar abstraction level, similar information density, clear logical progression — not identical syntax.

## 58. Parallel Wording inside recommendations

This is where syntax should often be stricter. Bad: `Supplier consolidation / Automating invoice processing / We should improve price discipline`. Normalize to:

```
Consolidate suppliers to reduce procurement complexity
Automate invoice processing to remove manual effort
Tighten pricing discipline to protect gross margin
```

Pattern: `VERB + OBJECT + TO + OUTCOME`.

## 59. Parallel Wording for design principles

Bad: `Customer focused / Make decisions locally / Simple / Scalable organisation`. Normalize to one family such as:

```
Put customer outcomes at the centre of decisions
Push accountability to the lowest effective level
Keep governance simple and explicit
Scale capabilities without duplicating roles
```

## 60. Parallel Wording for process steps

Bad: `1. Data / 2. Analyse results / 3. Recommendation is developed / 4. Implementation`. Good:

```
1. Collect the relevant data
2. Diagnose the performance gap
3. Define the recommended actions
4. Implement and track delivery
```

## 61. Parallel Wording for options

Bad: `Option A — Lowest cost / Option B — Faster implementation / Option C — This option maximises strategic flexibility`. Good:

```
Option A — Minimise upfront cost
Option B — Accelerate implementation
Option C — Maximise strategic flexibility
```

## 62. Repetition control

Parallel wording must not become repetitive wording. Bad:

```
Improve pricing to improve margin
Improve procurement to improve costs
Improve operations to improve productivity
```

Structure is parallel but language is poor. Add advisory checks for: same opening verb repeated excessively; same phrase repeated; generic verbs; low-information verbs. Encourage lexical precision while retaining grammatical symmetry.

## 63. Page-turn logic

Add a sequential check between headlines. Every headline should answer or naturally follow the previous one. Conceptually: Slide N: what is true? N+1: why? N+2: so what? N+3: what should we do? N+4: what does it deliver? The sequence does not need those exact roles, but transitions should be intelligible.

## 64. Story role metadata

Allow each slide to expose `{"story_role": "diagnosis"}`. Possible roles: context, problem, diagnosis, driver, implication, option, recommendation, impact, plan, risk, decision. This helps both ATE and horizontal-logic checks.

## 65. Prevent label headlines

In strict mode, generic topic titles on substantive slides should fail: Market overview; Revenue evolution; Financial performance; Cost analysis; Customer segmentation; Key findings; Strategic priorities; Next steps; Current situation; Competitive landscape — unless the slide is deliberately a divider or structural page.

## 66. Avoid "consulting-sounding" nonsense

ATE must not reward phrases merely because they sound executive: `Unlocking sustainable value through strategic transformation`, `Driving growth through a differentiated value proposition`, `Building the foundations for long-term success` — unless these statements actually encode a supported proposition. A precise plain sentence is preferable.

## 67. Preserve the deck language

ATE must preserve English → English and Spanish → Spanish unless explicitly requested otherwise. Do not produce hybrid wording such as `Repricing electrónica unlocks 1.4 pp de margen`.

## 68. Spanish support

Spanish cannot simply be treated as translated English. Support sentence patterns and verb detection independently:

```
El mix de electrónica explica la mayor parte de la caída del margen
Repreciar electrónica permitiría recuperar ~1,4 pp de margen
Tres regiones concentran el 72% de la brecha de EBITDA
```

Parallel Spanish recommendation pattern: `VERBO EN INFINITIVO + OBJETO + PARA + RESULTADO`:

```
Consolidar proveedores para reducir complejidad
Automatizar facturación para eliminar trabajo manual
Reforzar disciplina de precios para proteger margen
```

## 69. Capitalization

Default MBB-style editorial rule: sentence case, not Title Case — unless the corporate brand explicitly overrides it.

## 70. Punctuation

Action titles should normally not require a terminal period. Consistency matters more than the specific convention. PWG should detect mixed `Headline one. / Headline two / Headline three.` within the same deck/profile. Corporate profile may override.

## 71. Source lines and action titles

Source lines are not part of editorial parallelism. Do not modify `Source:`, `Fuente:` or other attribution text.

## 72. Archetype awareness

ATE should know the slide archetype.

- **KPI hero** — headline should express the significance of the KPI, not repeat its label. Bad: `2026 EBITDA`. Better: `EBITDA is €8m below plan despite revenue remaining on target`.
- **Waterfall** — headline should explain the bridge: `Electronics mix accounts for most of the 1.9 pp margin decline`.
- **Comparison** — headline should identify the meaningful difference: `Option B delivers similar value with half the implementation time`.
- **Process** — headline should communicate what the process achieves or how it changes: `A four-step triage removes two manual handoffs from the current process`.
- **Roadmap** — avoid simply `Implementation roadmap`. Prefer `Three waves can deliver the target model by Q4 2027`.

## 73. Candidate ranking

When multiple candidates exist, rank them lexicographically by:

1. hard semantic validity
2. proposition fidelity
3. evidence support
4. correct headline type
5. one-message discipline
6. answer-first strength
7. specificity
8. so-what
9. concision
10. wording cleanliness

Do not choose a prettier sentence that weakens factual fidelity.

## 74. No hidden semantic edits

ATE may alter wording, syntax, word order, verb choice, compression. It may not silently alter numbers, sign, direction, scope, timeframe, entity, recommendation, causal strength, confidence. Any change to those belongs upstream in reasoning.

## 75. Editorial compiler

Create an orchestration layer `def compile_editorial(spec, profile=None): ...`. Suggested sequence:

1. normalize propositions
2. validate proposition lineage
3. classify headline type
4. collect/generate headline candidates
5. validate candidates
6. select candidate
7. detect parallel groups
8. establish group signatures
9. normalize / request rewrites
10. validate parallel groups
11. run horizontal-logic checks
12. produce editorial report
13. return compiled spec

## 76. Idempotence

Editorial compilation must be idempotent. Running `compile_editorial()` twice on an already passing spec should not continuously rewrite wording. This is essential for the current iterative render/autofix architecture.

## 77. Autofix interaction

Visual autofix should never rewrite semantic wording to solve a layout problem. If a title is too long, the bad fix is to automatically delete meaningful words. Correct order: try layout / title geometry → if still problematic → `EDITORIAL_HEADLINE_FIT` warning → request semantically safe compression. Semantic compression must return through ATE.

## 78. Composition interaction

Composition candidates must all use the exact same compiled headline. Do not allow different layout candidates to receive different wording, otherwise composition scoring becomes confounded by editorial changes.

## 79. Corporate templates

Action-title requirements should survive corporate adaptation. Corporate brand can control font, size, weight, position, capitalization preference and punctuation preference, but cannot convert a conclusion headline into a topic label unless the user explicitly chooses a non-MBB editorial mode.

## 80. CLI additions

- `cpe editorial check deck.json` — headline QA, parallel groups, horizontal logic, editorial status.
- `cpe editorial explain deck.json` — detailed diagnostics: slide, proposition, selected headline, headline type, evidence, score, issues, parallel group, signature.
- `cpe editorial ghost deck.json` — creates `headline_strip.md` and `editorial_ghost_deck.md`.
- Optional: `cpe editorial normalize deck.json -o deck.editorial.json` for legacy specs.

## 81. Output artifacts

Every normal run should contain `editorial_report.json`, `editorial_report.md`, `headline_strip.md`, `ghost_deck.md`, alongside `resolved.json`, `build_manifest.json`, `qa_report.json`, `qa_report.md`.

## 82. QA summary

`qa_report.md` should show:

```
Factual QA        PASSED
Editorial QA      PASSED
Visual QA         PASSED
Authoring QA      PASSED
Brand QA          PASSED
```

Do not hide editorial quality inside a generic total score.

## 83. Editorial failure behavior

For `mbb_strict`: hard editorial error → deck may still be rendered for debugging → final status = FAILED. This is analogous to visual QA. A user can inspect the output but cannot mistake it for an approved result.

## 84. Tests — Action Title Engine

Create `tests/test_action_titles.py`. Cover at least: topic label rejected; complete conclusion accepted; unsupported number rejected; derived supported number accepted; unsupported causal claim rejected; supported causal claim accepted; direction reversal rejected; timeframe drift rejected; entity drift rejected; two governing messages rejected; vague unquantified claim flagged; question headline flagged; recommendation without recommendation proposition rejected; comparison without comparison evidence rejected; Spanish topic label rejected; Spanish conclusion accepted; English conclusion accepted; cover exempt; divider exempt.

## 85. Tests — proposition fidelity

Create `tests/test_proposition_fidelity.py`. Test changes in sign, direction, magnitude, scope, entity, time, confidence, causal strength, recommendation. Example: proposition `Sales grew 8%`, candidate `Sales fell 8%` — must hard fail.

## 86. Tests — Parallel Wording Guarantee

Create `tests/test_parallel_wording.py`. Cases: three verb-led recommendations → pass; noun / verb / clause mixture → fail; same syntax but different semantic granularity → fail/warn; active/passive mixture → warn/fail depending group; mixed tense → fail; consistent process steps → pass; Spanish infinitive recommendations → pass; English imperative recommendations → pass; different narrative slide roles → do not force into same group; repeated identical verb → advisory only; punctuation mismatch → detect.

## 87. Tests — pipeline integration

Create `tests/test_editorial_pipeline.py`. Ensure: ATE runs before planner; ATE runs before compose; planner still runs existing headline lint; final resolved spec contains editorial metadata; editorial report is written; failing editorial QA affects final pass/fail; visual autofix does not alter accepted headline semantics.

## 88. Tests — update workflow

Create `tests/test_editorial_update.py`. Cases: headline still holds → preserved; number changes, claim still holds → wording updated safely; claim no longer holds → proposition rebuilt → ATE invoked; old topic title preserved in normal update mode; old topic title normalized with `--normalize-editorial`; rebuilt slide always goes through ATE; `set_headline` remains unapproved until human approval.

## 89. Tests — parallel group integration

Ensure parallel checks cover exec summary, process, roadmap, recommendation cards, comparison columns, key-line arguments, design principles.

## 90. Regression suite

Add a dedicated editorial fixture set, `evals/editorial/`. Include at least:

```
50 valid headlines
50 invalid headlines
30 proposition-drift cases
25 unsupported-causality cases
25 numeric-support cases
20 Spanish cases
20 English cases
20 parallel groups
10 deliberately non-parallel groups that must NOT be normalized
```

Do not tune against a single deck.

## 91. Adversarial cases

Especially test: headlines that sound good but are false; headlines with correct number but wrong entity; correct entity but wrong year; correct values but reversed comparison; correlation rewritten as causality; observation rewritten as recommendation; recommendation rewritten as decision; approximate numbers made exact; direction removed during compression. These are more dangerous than bad grammar.

## 92. Human evaluation

Use the existing human-evaluation infrastructure where practical. Create a specific editorial round. Two evaluation surfaces:

- **Headline only** — show proposition, evidence summary, headline A, headline B. Ask: *Which is the stronger consulting action title? A / B / tie*.
- **Full-slide context** — show rendered slide A and B. Evaluate clarity, answer-first quality, specificity, executive readability, factual fidelity.

Do not fabricate votes.

## 93. Headline-strip human evaluation

A second useful human task: show only the full sequence of action titles. Ask: *Can you reconstruct the deck's argument without opening the slides?* This directly tests horizontal logic.

## 94. Evaluation signals

Report editorial evaluation separately: action-title hard pass rate; mean headline diagnostic score; topic-title rate; proposition-fidelity failures; unsupported-claim rate; parallel-group pass rate; headline-strip coherence; human preference. No composite with composition score.

## 95. Suggested release gates

For `v3.1.0`:

```
0 unsupported quantitative claims
0 proposition-direction mismatches
0 unsupported causal claims
0 unresolved topic titles on strict content slides
100% mandatory parallel groups structurally compliant
100% content slides have proposition lineage
0 regression in existing factual QA
0 regression in existing visual hard QA
255+ existing tests continue to pass
all new editorial tests pass
```

Do not require a perfect stylistic score. Require semantic correctness and structural compliance.

## 96. Existing visual scores must not be gamed

Do not change visual archetype profiles merely because new action titles alter title geometry. If action titles reveal a genuine layout weakness, fix layout behavior. Do not weaken the metric to preserve the score.

## 97. Existing factuality must not regress

This is the most important implementation rule. ATE/PWG may make the language stronger stylistically. They must never make the claims stronger epistemically.

Allowed: `Most margin erosion is concentrated in electronics` → `Electronics accounts for most of the margin erosion`, if proven.

Not allowed: `Electronics margin erosion coincides with a mix shift` → `The mix shift caused electronics margin erosion`, unless causality is proven.

## 98. Backwards compatibility

Old `deck.json` files without `proposition` should continue to load.

- `legacy` — no mandatory migration.
- `standard` — infer provisional proposition from headline, purpose, message_type, evidence, and warn.
- `mbb_strict` — require a validated proposition before passing final editorial QA.

## 99. Migration of examples

Update development examples to include propositions. Do not manually write propositions simply to satisfy schema. They must match existing slide meaning and evidence. Then run regression, robustness, reproducibility, visual QA, editorial QA.

## 100. Documentation

Add `docs/EDITORIAL_LAYER.md`, `docs/ACTION_TITLE_ENGINE.md`, `docs/PARALLEL_WORDING.md`, `docs/HEADLINE_STYLE.md`. Update `README.md`, `docs/ARCHITECTURE.md`, `docs/EVALS.md`.

## 101. Architecture documentation

Architecture should explicitly become:

```
INPUT → CONTENT UNDERSTANDING → FACT MODEL → ANALYSIS → HYPOTHESES / INSIGHTS → STORYLINE
→ SLIDE INTENT → PROPOSITION → ACTION TITLE ENGINE → PARALLEL WORDING GUARANTEE → EDITORIAL QA
→ EVIDENCE → VISUAL ENCODING → LAYOUT SELECTION → SLIDE SPECIFICATION → PPTX GENERATION
→ RENDER → VISUAL QA → ITERATION → FINAL PPTX
```

## 102. Key architecture distinction

There must be three separate objects: PURPOSE, PROPOSITION, HEADLINE.

- Purpose: `Show why gross margin declined`
- Proposition: `The shift toward electronics explains most of the gross-margin decline`
- Headline: `Electronics mix explains most of the 1.9 pp gross-margin decline`

They are not interchangeable.

## 103. Purpose is not a headline

Reject `Explain the causes of the margin decline`. That is an instruction to the slide author.

## 104. Proposition is not always final copy

This may be correct semantically: `There was a 1.9 percentage-point decline in gross margin and most of the decline can be attributed to changes in product mix toward electronics`. But the action title can compress it to `Electronics mix explains most of the 1.9 pp gross-margin decline`. That is exactly why proposition and headline need separate representations.

## 105. Headline is not evidence

The headline states the answer. The visual proves it. Do not overcrowd the title with every supporting fact.

## 106. Parallel wording is not content homogenisation

Do not normalize diagnosis, recommendation and impact into the same syntax simply because they are consecutive. Parallelism applies to comparable elements, not to the full narrative indiscriminately.

## 107. Implementation phases

1. **Semantic contract** — proposition schema, proposition validation, backwards compatibility, editorial metadata. No wording changes yet.
2. **Action Title Engine** — candidate contract, headline classification, proposition fidelity, hard semantic gates, integration with existing headline.py, candidate ranking, editorial report.
3. **Pipeline integration** — insert compiler before compose and plan. Keep planner lint as defense in depth.
4. **Parallel Wording Guarantee** — parallel group detection, explicit group support, wording signatures, structural QA, semantic granularity QA, group reporting.
5. **Storyline / ghost deck** — headline strip, parallel annotations, horizontal-logic diagnostics.
6. **Existing deck updates** — integrate into reasoning/messages.py, reasoning/update.py, reasoning/rebuild.py without weakening the human approval workflow.
7. **Tests and evals** — add all editorial suites. Run full existing suite unchanged.
8. **Documentation** — update product architecture and user guide.

## 108. Files expected to change

At minimum: `src/cpe/pipeline.py`, `src/cpe/spec.py`, `src/cpe/core/planner.py`, `src/cpe/core/headline.py`, `src/cpe/core/storyline.py`, `src/cpe/reasoning/messages.py`, `src/cpe/reasoning/update.py`, `src/cpe/reasoning/rebuild.py`, `src/cpe/cli.py`, `src/cpe/eval.py`.

New: `src/cpe/editorial/{__init__,compiler,proposition,action_titles,parallel,signatures,qa,report}.py`.

Tests: `tests/test_action_titles.py`, `tests/test_proposition_fidelity.py`, `tests/test_parallel_wording.py`, `tests/test_editorial_pipeline.py`, `tests/test_editorial_update.py`.

Evals: `evals/editorial/`.

Docs: `docs/EDITORIAL_LAYER.md`, `docs/ACTION_TITLE_ENGINE.md`, `docs/PARALLEL_WORDING.md`.

## 109. Do not create a second rendering loop

ATE/PWG belongs before rendering. Do not implement render → vision model thinks headline is weak → rewrite → render again as the primary mechanism. That would be expensive and conceptually wrong. Semantic/editorial quality should be settled before visual rendering. Render can still detect widows, line count, clipping, fit.

## 110. Do not implement an MBB phrase dictionary

Avoid an engine that swaps increase → accelerate, good → compelling, change → transformation. That produces consulting parody. The desired quality comes from logic, specificity, evidence, compression, hierarchy, parallel structure — not jargon.

## 111. Do not optimise for length alone

A short topic label is worse than a slightly longer conclusion. Bad: `Pricing opportunity`. Better: `Pricing can recover ~1.4 pp of margin without reducing volume`. The action title budget exists to force compression, not to remove the answer.

## 112. Do not force numbers into every title

The existing headline system encourages quantified titles when data exists. Keep that preference but not as an absolute rule. `A fragmented ownership model prevents end-to-end accountability` can be a stronger action title than an irrelevant number. Quantification should increase specificity when it strengthens the proposition.

## 113. MBB strict contract

The most important new invariant:

> No substantive slide reaches final output unless its title expresses an evidence-backed proposition rather than merely naming its topic.

Second invariant:

> No set of logically equivalent messages reaches final output with inconsistent grammatical or semantic structure.

These are the two product guarantees.

## 114. Definition of done

**Semantic architecture** — `proposition` is a first-class concept; purpose, proposition and headline are distinct; every strict content slide has a proposition; every proposition references evidence or reasoning.

**Action titles** — ATE is integrated before composition and planning; topic titles fail strict editorial QA; unsupported numbers fail; unsupported causal language fails; direction, entity, scope and timeframe cannot silently drift; existing headline lint remains active; covers/dividers are correctly exempt.

**Parallel wording** — explicit parallel groups are supported; automatic grouping is conservative; structural signatures exist; mandatory sibling groups are validated; meaning outranks symmetry; Spanish and English are supported.

**Storyline** — ghost-deck logic remains; headline strip is generated; key-line arguments can be checked for parallel wording; executive-summary statements receive strict treatment.

**Update workflow** — headlines that still hold remain unchanged by default; changed messages are routed through ATE; rebuilt slides are routed through ATE; `--normalize-editorial` exists for deliberate full-deck clean-up; human approval remains required for changed existing-deck headlines.

**QA** — editorial QA is a separate first-class signal; editorial hard errors affect final pass/fail; visual QA remains independent; factual QA remains independent; brand QA remains independent.

**Engineering** — existing tests remain green; new editorial tests are green; regression does not deteriorate; reproducibility remains intact; no private corporate material enters the repo; no new external model dependency is required by the core package; compilation is deterministic once headline candidates/propositions are fixed; editorial compilation is idempotent.

## 115. Release positioning

If these two capabilities are part of the product definition, then do not describe them as post-v3 polish. Treat the release as **v3.1.0 — Editorial Logic Layer** (or equivalently *MBB Editorial Closure*).

The release thesis: MBBslides already guarantees analytical, visual and technical quality; v3.1 adds a formal guarantee that the language of the deck also follows consulting logic: every substantive slide communicates an evidence-backed takeaway, and equivalent messages are expressed in parallel form.

## 116. Final target architecture

```
RAW SOURCES
  ↓
FACT MODEL (lineage + provenance)
  ↓
ANALYSIS (calculations / models)
  ↓
HYPOTHESES / INSIGHTS
  ↓
STORYLINE (pyramid / key line)
  ↓
SLIDE INTENT (purpose + story role)
  ↓
SLIDE PROPOSITION (exact semantic claim + evidence)
  ↓
ACTION TITLE ENGINE (proposition → executive wording)
  ↓
PARALLEL WORDING GUARANTEE (sibling logic + syntax)
  ↓
EDITORIAL QA (vertical + horizontal logic)
  ↓
VISUAL REASONING (chart/table/diagram)
  ↓
LAYOUT + COMPOSITION
  ↓
DECK.JSON (source of truth)
  ↓
NATIVE PPTX
  ↓
RENDER
  ↓
VISUAL QA
  ↓
FINAL PPTX
```

## 117. Core principle

```
Every slide has a reason to exist.
Every slide makes one proposition.
Every proposition is supported.
Every substantive headline states that proposition.
Every visual proves the headline.
Every sibling message is written as a sibling.
Every page contributes to the governing thought.
```

That is the target editorial contract for MBBslides.

## 118. Instruction to Claude Code

Implement this specification end-to-end in the current MBBslides repository. Do not treat Action Title Engine or Parallel Wording Guarantee as optional cosmetic features. They are a new Editorial Logic Layer positioned after storyline/slide-intent reasoning and before composition/planning/rendering.

Before modifying code:

1. inspect the current implementations of `src/cpe/core/headline.py`, `src/cpe/core/storyline.py`, `src/cpe/core/planner.py`, `src/cpe/pipeline.py`, `src/cpe/spec.py`, `src/cpe/reasoning/messages.py`, `src/cpe/reasoning/update.py`, `src/cpe/reasoning/rebuild.py`, and the existing QA/eval/human-eval infrastructure;
2. reuse rather than duplicate existing functionality;
3. preserve all existing factuality, lineage, update-review and visual-QA guarantees.

Implementation principles:

- `deck.json` remains the only slide source of truth.
- Add `proposition`; do not create a competing deck format.
- Preserve `headline` as the final rendered string.
- Existing `headline.py` remains a defensive deterministic validator and should be reused by ATE.
- ATE must execute before `compose()` and `plan()`.
- Planner should continue independently linting final headlines.
- PWG operates on explicit or confidently inferred sibling groups, not indiscriminately across the entire deck.
- Truth always outranks parallelism.
- Do not invent numbers, causes, recommendations, decisions or implications.
- Do not weaken existing QA/eval thresholds to make the implementation pass.
- Do not add a mandatory external LLM/API dependency to the package.
- Candidate wording may come from the reasoning agent; deterministic acceptance/rejection belongs to MBBslides.
- Implement safe deterministic rewrites only where proposition semantics fully determine them.
- If a strict slide cannot obtain an acceptable headline, fail closed with a clear editorial issue.
- Keep editorial QA independent from visual composition, brand fidelity and factual QA.
- Integrate changed/rebuilt headlines into the current update workflow without removing human approval.
- Preserve current private-material guarantees.

Add complete tests, editorial fixtures, reports, CLI commands and documentation described above. Run the entire existing suite plus the new tests.

Do not release `v3.1.0` merely because tests execute. Release only when the Definition of Done above is met and existing regression/reproducibility/factuality guarantees remain intact.
