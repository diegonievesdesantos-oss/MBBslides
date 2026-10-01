# Brief for an external deck author

*Give this page (and only this page plus docs/SPEC_REFERENCE.md) to the person who writes the
external holdout. Do not show them any rendered slide, eval result, regression case or internal
document of MBBslides.*

## What we ask

Write **15–30 realistic presentation decks** as JSON files in the MBBslides spec format
(docs/SPEC_REFERENCE.md; one example deck is enough to learn it). Each deck: 6–15 slides.

Write them the way you would write a real deck for a real client or board:

- a real question and an answer (the governing thought), not a list of topics;
- slide headlines that state a conclusion ("Churn doubled in the north after the price change"),
  with the numbers that prove them in the exhibit (chart / table / KPIs / process / text);
- the evidence you would actually show — whatever chart, table or diagram you would choose.

Cover a mix of contexts — strategy, board, commercial, financial, operations, transformation,
product, market, sales, public sector, investment / due diligence — in **English and Spanish**, and
mix dense and sparse slides. Bad or unusual decks are welcome: they are evidence too.
Use fictitious or anonymized companies and figures.

## What not to do

- Do not use MBBslides to render or preview your decks (you may run `cpe lint` to check the format).
- Do not ask the developers what the engine is good or bad at.

## Handing over

Put the files in a folder `decks/` and fill in `PROVENANCE.json`:

```json
{
  "author_role": "e.g. strategy consultant, 6 years",
  "authored_by_developer": false,
  "engine_renders_seen_by_author": false,
  "received": "YYYY-MM-DD",
  "notes": "how the decks were written (from real projects, anonymized / from scratch / other AI agent without access to MBBslides internals)"
}
```

Zip both and send them to the project owner. They will be hashed and sealed on arrival and run
exactly once on a frozen engine.
