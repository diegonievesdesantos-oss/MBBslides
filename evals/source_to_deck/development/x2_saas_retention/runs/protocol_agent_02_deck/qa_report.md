# QA report

**Verdict:** ✅ PASSED · **Deck score:** 95.0/100 · errors 0 · warnings 11 · info 5

## Iterations (generate → render → inspect → patch)

| # | errors | warnings | score | patches applied |
|---|---|---|---|---|
| 1 | 0 | 11 | 95.0 | — |

## Actions for the author (cannot be auto-fixed without changing the message)

- **S2** `HEADLINE_LONG` — Cut the headline to the claim.
- **S2** `DENSITY_WORDS` — Cut words: keep only what proves the headline.
- **S4** `HEADLINE_LONG` — Cut the headline to the claim.
- **S4** `HEADLINE_TWO_MESSAGES` — Keep one claim in the headline; move the other to the commentary or its own slide.
- **S5** `HEADLINE_TWO_MESSAGES` — Keep one claim in the headline; move the other to the commentary or its own slide.
- **S6** `HEADLINE_LONG` — Cut the headline to the claim.
- **S6** `HEADLINE_TWO_MESSAGES` — Keep one claim in the headline; move the other to the commentary or its own slide.
- **S7** `HEADLINE_LONG` — Cut the headline to the claim.
- **S8** `HEADLINE_LONG` — Cut the headline to the claim.
- **S9** `HEADLINE_LONG` — Cut the headline to the claim.

## Slide scores

| slide | score | errors | warnings |
|---|---|---|---|
| S1 | 100 | 0 | 0 |
| S2 | 92 | 0 | 2 |
| S3 | 100 | 0 | 0 |
| S4 | 92 | 0 | 2 |
| S5 | 95 | 0 | 1 |
| S6 | 92 | 0 | 2 |
| S7 | 95 | 0 | 1 |
| S8 | 95 | 0 | 1 |
| S9 | 94 | 0 | 1 |

## Issues

### deck
- **warning** `STORY_GT_LONG` — Governing thought over 35 words: it should fit in one breath

### S2
- **warning** `HEADLINE_LONG` — Headline has 26 words (budget 18); cut to the claim
- **warning** `DENSITY_WORDS` — 121 words on the slide (budget 112 for this deck profile)

### S4
- **warning** `HEADLINE_LONG` — Headline has 27 words (budget 18); cut to the claim
- **warning** `HEADLINE_TWO_MESSAGES` — Headline joins two claims; one slide = one message (split the slide or subordinate one claim)

### S5
- **warning** `HEADLINE_TWO_MESSAGES` — Headline joins two claims; one slide = one message (split the slide or subordinate one claim)
- **info** `VIS_OFF_MESSAGE` — 'column' is not a usual encoding for a comparison message; consider 'harvey_table' (options × criteria with qualitative ratings)

### S6
- **warning** `HEADLINE_LONG` — Headline has 22 words (budget 18); cut to the claim
- **warning** `HEADLINE_TWO_MESSAGES` — Headline joins two claims; one slide = one message (split the slide or subordinate one claim)

### S7
- **warning** `HEADLINE_LONG` — Headline has 28 words (budget 18); cut to the claim
- **info** `VIS_OFF_MESSAGE` — 'waterfall' is not a usual encoding for a comparison message; consider 'harvey_table' (options × criteria with qualitative ratings)

### S8
- **warning** `HEADLINE_LONG` — Headline has 26 words (budget 18); cut to the claim
- **info** `VIS_OFF_MESSAGE` — 'waterfall' is not a usual encoding for a comparison message; consider 'harvey_table' (options × criteria with qualitative ratings)

### S9
- **warning** `HEADLINE_LONG` — Headline has 29 words (budget 18); cut to the claim
- **info** `DENSITY_LONG_BULLET` — Bullet of 20 words: lead with the point, cut the rest ('**Monthly:** first-year churn (from 26%), time to …')
- **info** `FIT_SHRUNK` — 'headline' shrunk 23.0→21.5 pt to fit

