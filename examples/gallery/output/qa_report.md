# QA report

**Verdict:** ✅ PASSED · **Deck score:** 98.5/100 · errors 0 · warnings 8 · info 7

## Iterations (generate → render → inspect → patch)

| # | errors | warnings | score | patches applied |
|---|---|---|---|---|
| 1 | 0 | 8 | 98.5 | — |

## Actions for the author (cannot be auto-fixed without changing the message)

- **g07** `COMPOSITION_PROOF_NOT_VISIBLE` — Make the headline's number / item visible in the exhibit (label or highlight it).
- **g13** `COMPOSITION_NOISY_EMPHASIS` — Keep one highlight; grey the context.
- **g14** `COMPOSITION_DEAD_SPACE` — Content too thin for a full slide: add the proof or merge into a neighbouring slide.
- **g14** `COMPOSITION_UNDERUSED_CANVAS` — Give the exhibit more data/proof or merge the slide.
- **g18** `COMPOSITION_DEAD_SPACE` — Content too thin for a full slide: add the proof or merge into a neighbouring slide.
- **g18** `COMPOSITION_UNDERUSED_CANVAS` — Give the exhibit more data/proof or merge the slide.
- **g19** `COMPOSITION_DEAD_SPACE` — Content too thin for a full slide: add the proof or merge into a neighbouring slide.
- **g19** `COMPOSITION_UNDERUSED_CANVAS` — Give the exhibit more data/proof or merge the slide.

## Slide scores

| slide | score | errors | warnings |
|---|---|---|---|
| g01 | 100 | 0 | 0 |
| g02 | 100 | 0 | 0 |
| g03 | 100 | 0 | 0 |
| g04 | 100 | 0 | 0 |
| g05 | 100 | 0 | 0 |
| g06 | 100 | 0 | 0 |
| g07 | 96 | 0 | 1 |
| g08 | 100 | 0 | 0 |
| g09 | 100 | 0 | 0 |
| g10 | 99 | 0 | 0 |
| g11 | 100 | 0 | 0 |
| g12 | 100 | 0 | 0 |
| g13 | 95 | 0 | 1 |
| g14 | 91 | 0 | 2 |
| g15 | 100 | 0 | 0 |
| g16 | 99 | 0 | 0 |
| g17 | 100 | 0 | 0 |
| g18 | 92 | 0 | 2 |
| g19 | 92 | 0 | 2 |
| g20 | 100 | 0 | 0 |
| g21 | 99 | 0 | 0 |
| g22 | 100 | 0 | 0 |
| g23 | 100 | 0 | 0 |
| g24 | 99 | 0 | 0 |
| g25 | 99 | 0 | 0 |
| g26 | 100 | 0 | 0 |

## Issues

### g10
- **info** `VIS_OFF_MESSAGE` — 'stacked_100' is not a usual encoding for a composition message; consider 'bar' (sorted bars compare parts more precisely than angles)

### g13
- **warning** `COMPOSITION_NOISY_EMPHASIS` — Too much in the focus colour: keep one highlight and grey the context. (composition score 86)
- **info** `HEADLINE_UNQUANTIFIED` — Data slide without a number in the headline; the strongest action titles quantify

### g21
- **info** `HEADLINE_UNQUANTIFIED` — Data slide without a number in the headline; the strongest action titles quantify

### g24
- **info** `HEADLINE_UNQUANTIFIED` — Data slide without a number in the headline; the strongest action titles quantify

### g25
- **info** `VIS_BETTER_OPTION` — 'bar' fits a composition message better than 'donut' (sorted bars compare parts more precisely than angles)

### g14
- **warning** `COMPOSITION_DEAD_SPACE` — Even the best composition leaves a large empty area: the content is too thin for a full slide — add the proof (numbers, comparison) or merge it into a neighbouring slide. (composition score 61)
- **warning** `COMPOSITION_UNDERUSED_CANVAS` — The exhibit uses little of the slide: give it more data/proof or merge the slide. (composition score 61)
- **info** `RENDER_UNBALANCED` — 16/32 body cells empty next to dense content: check balance

### g16
- **info** `RENDER_UNBALANCED` — 20/32 body cells empty next to dense content: check balance

### g07
- **warning** `COMPOSITION_PROOF_NOT_VISIBLE` — The headline's number or highlighted item is not visible in the exhibit: label it or highlight it. (composition score 78)

### g18
- **warning** `COMPOSITION_DEAD_SPACE` — Even the best composition leaves a large empty area: the content is too thin for a full slide — add the proof (numbers, comparison) or merge it into a neighbouring slide. (composition score 63)
- **warning** `COMPOSITION_UNDERUSED_CANVAS` — The exhibit uses little of the slide: give it more data/proof or merge the slide. (composition score 63)

### g19
- **warning** `COMPOSITION_DEAD_SPACE` — Even the best composition leaves a large empty area: the content is too thin for a full slide — add the proof (numbers, comparison) or merge it into a neighbouring slide. (composition score 72)
- **warning** `COMPOSITION_UNDERUSED_CANVAS` — The exhibit uses little of the slide: give it more data/proof or merge the slide. (composition score 72)

