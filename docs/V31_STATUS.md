# v3.1 status — Editorial Logic Layer

Specification: [V31_SPEC.md](V31_SPEC.md) (saved as given). Design: [EDITORIAL_LAYER.md](EDITORIAL_LAYER.md),
[ACTION_TITLE_ENGINE.md](ACTION_TITLE_ENGINE.md), [PARALLEL_WORDING.md](PARALLEL_WORDING.md),
[HEADLINE_STYLE.md](HEADLINE_STYLE.md). Engine frozen at `dcb4232`; every number below was measured on it.

## How it was evaluated

Two fixture sets were written by two separate agents who read only the specification and the fixture
schema, never the engine's code:

- **dev**, 210 cases (113 EN / 97 ES): used while building the engine. In-sample.
- **holdout**, 111 cases (58 EN / 53 ES): sealed (sha256, `evals/editorial/holdout/SEAL.json`, committed
  in `f4cb96f` before the engine existed); run **once** on the frozen engine; not used to tune anything
  afterwards.

Each case states the author's verdict (pass / fail with acceptable codes / a selected candidate; for
parallel groups pass / fail / flagged; for sequences "leave alone"). Agreement = the engine's outcome
matches that verdict.

## Results

| signal | dev (in-sample) | **holdout (blind, once)** |
|---|---|---|
| agreement | 99.5% (209/210) | **92.8% (103/111)** |
| valid headlines accepted | 100% | **97.6%** |
| failing headlines caught with an acceptable code | 99.0% | **88.2%** |
| unsupported claims let through (numeric, causal, drift) | 0 / 49 | **3 / 26** |
| parallel groups judged as the author did | 100% | **91.7%** |
| non-parallel sequences left alone | 100% | **100%** |
| by language EN / ES | 99.1% / 100% | **89.7% / 96.2%** |

The first dev run, before any development on it, agreed on 76.7%: the dev figure is the result of
working on that set and is not evidence of generalisation. The holdout figure is.

### The 8 blind disagreements (diagnosed after the run; not fixed in 3.1.0)

- **3 — a criterion disagreement, not an error of the engine's rules.** A topic label ("Market overview",
  "Cost analysis by business unit", "Net promoter score (NPS), Q2 2026") on a slide whose proposition is a
  complete factual trend (subject, direction, magnitude, period). The engine applies the safe rewrite
  the specification allows (§11) and the slide passes with the rewritten title; the authors expected the
  slide to fail closed. Same disagreement as the one dev miss.
- **3 — real misses (something unsupported got through):**
  - a scope dropped entirely ("Revenue grew 15%" for *online channel* revenue: the scope check only fires
    when part of the scope is still named);
  - a Spanish infinitive recommendation on an observation ("Elegir la opción A para capturar…");
  - a percentage that is not derivable (40% where the evidence gives 2,100 of 7,000 = 30%).
- **2 — false rejections:** a plural verb the lexicon does not know ("Online orders carry 1.5× …"
  read as a label) and a plural noun inside an instruction read as a verb ("… by tightening quality
  checks at intake").

These are listed for the next round; fixing them now would be tuning on the sealed set.

## Release gates (spec §95)

| gate | status |
|---|---|
| 0 unsupported quantitative claims · 0 direction mismatches · 0 unsupported causal claims · 0 unresolved topic titles — on the strict decks the engine ships (the 3 examples) | met: the three example decks pass strict editorial QA with 0 hard findings |
| the same, as detection on unseen material | **not met on the blind holdout: 3 of 26 unsupported claims passed** (see above) |
| 100% mandatory parallel groups structurally compliant (examples) | met (alvora 3/3, gallery 4/4, alvora on Kestrel 3/3) |
| 100% content slides with proposition lineage (examples) | met (11 + 21 + 11 explicit propositions, every one citing evidence ids) |
| 0 regression in factual / visual hard QA | met: regression 95.1 with 0 QA errors, examples 99.6, robustness 0 drop (same as 3.0.0) |
| 255+ existing tests pass; new editorial tests pass | met: 338 tests (255 existing, unchanged, + 83 new) |

## Existing guarantees

Release evaluations, recorded on the frozen engine (Docker, pinned environment):

| suite | 3.0.0 | **3.1.0** |
|---|---|---|
| regression (composition, archetype fitness) | 95.1, 0 QA errors | **95.1, 0 QA errors** (visual 0, authoring 0) |
| examples | 99.6 | **99.6**, all three decks PASSED (the gate now includes strict editorial QA) |
| robustness | 0 drop over 78 variants | **median drop 0.0, P90 0.0, 0 catastrophic over 78 variants** |

No headline of the regression cases or the examples changed: the editorial layer added a verdict, not
a rewrite. Composition and visual QA are unchanged.

## Definition of done (spec §114)

- Proposition is first-class; purpose, proposition and headline are separate fields; strict slides need
  one; every proposition must cite evidence/analysis ids that resolve. — done
- ATE runs before composition and planning; topic titles, unsupported numbers and causal language fail;
  direction, entity, scope and period drift fail (with the blind misses above); the planner's lint is
  unchanged and still runs; covers/dividers/agenda/closing are exempt. — done
- Explicit groups, conservative automatic groups, signatures, mandatory sibling groups, meaning over
  symmetry, English and Spanish. — done (comparison of qualifiers across members not implemented: see
  PARALLEL_WORDING.md)
- Ghost deck kept; headline strip and editorial ghost deck generated; key line and executive summary
  checked. — done
- Update workflow: holding headlines untouched; broken messages and rebuilt slides through the ATE;
  `--normalize-editorial`; human approval required. — done
- Editorial QA is its own verdict; hard errors fail the deck; visual, factual and brand QA independent. — done
- Deterministic and idempotent compilation; no new dependency; no private material in the repository. — done
- Human evaluation: round `evals/human_reference/rounds/e1/headlines` (7 pairs: the wording the engine
  rejected vs the one it selected, with proposition and evidence as context) is built and **awaits
  votes**; no vote was generated. A headline-strip round needs two runs of the same deck with different
  wording, which do not exist yet.

## What it does not do

It does not write headlines (the reasoning agent proposes, the engine accepts or rejects), it does not
understand the business (a wrong proposition stated faithfully passes), and its language checks are
lexical: unknown verb forms can make a conclusion look like a label, and entity drift is caught when the
entities are labelled in the evidence or exhibit.
