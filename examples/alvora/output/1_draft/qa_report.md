# QA report

**Verdict:** ❌ FAILED · **Deck score:** 95.8/100 · errors 2 · warnings 3 · info 4

## Iterations (generate → render → inspect → patch)

| # | errors | warnings | score | patches applied |
|---|---|---|---|---|
| 1 | 2 | 4 | 95.3 | VIS_TIME_VERTICAL |
| 2 | 2 | 3 | 95.8 | — |

## Actions for the author (cannot be auto-fixed without changing the message)

- **s03** `DENSITY_WORDS` — Cut words: keep only what proves the headline.
- **s07** `HEADLINE_TOPIC` — Replace the topic label with a conclusion: what does the data show, and so what?
- **s10** `HEADLINE_LONG` — Cut the headline to the claim.
- **s10** `HEADLINE_TWO_MESSAGES` — Keep one claim in the headline; move the other to the commentary or its own slide.
- **s12** `SOURCE_MISSING` — Add the source line (data slides must cite their source).

## Slide scores

| slide | score | errors | warnings |
|---|---|---|---|
| s01 | 100 | 0 | 0 |
| s02 | 100 | 0 | 0 |
| s03 | 95 | 0 | 1 |
| s04 | 100 | 0 | 0 |
| s05 | 100 | 0 | 0 |
| s06 | 100 | 0 | 0 |
| s07 | 79 | 1 | 0 |
| s08 | 100 | 0 | 0 |
| s09 | 100 | 0 | 0 |
| s10 | 91 | 0 | 2 |
| s11 | 100 | 0 | 0 |
| s12 | 84 | 1 | 0 |

## Issues

### s03
- **warning** `DENSITY_WORDS` — 123 words on the slide (budget 110 for this deck profile)
- **info** `DENSITY_LONG_BULLET` — Bullet of 32 words: lead with the point, cut the rest ('**Discount** grows 7.8% a year on price-sensitive …')

### s07
- **error** `HEADLINE_TOPIC` — 'Gross margin change by category and region' reads as a topic, not a conclusion. State what the data shows (subject + verb + so-what)
- **info** `HEADLINE_UNQUANTIFIED` — Data slide without a number in the headline; the strongest action titles quantify

### s10
- **warning** `HEADLINE_LONG` — Headline has 32 words (budget 20); cut to the claim
- **warning** `HEADLINE_TWO_MESSAGES` — Headline joins two claims; one slide = one message (split the slide or subordinate one claim)
- **info** `FIT_SHRUNK` — 'headline' shrunk 22.0→20.0 pt to fit

### s12
- **error** `SOURCE_MISSING` — Data slide without a source line
- **info** `HEADLINE_UNQUANTIFIED` — Data slide without a number in the headline; the strongest action titles quantify

