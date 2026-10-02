# v3.0 status (3.0.0.dev0): the last version

The owner closed v2.5 and asked for one last version. Its only criterion is the owner's real material.
No new matching rule is written for it, and only clear bugs found on that material are fixed.

| # | step | who | status |
|---|---|---|---|
| 1 | Real material: 2–3 update cases (old deck + this year's sources) and 3–5 unseen corporate templates | owner | **waiting** |
| 2 | A key sheet per case, from its old deck (`scripts/validation_kit.py template`) | tool | **ready** |
| 3 | The owner keys each sheet without seeing the tool's output; sha256 recorded before the run (`seal`) | owner, then tool | waiting |
| 4 | One blind run per case (`score`); a sample deck built on each template, QA'd and rated by the owner | tool, owner | waiting |
| 5 | Fix only clear bugs; final guide, measured limits; 3.0.0 | tool | waiting |

## Privacy

- **Where the material lives.** All of it stays in `.private/`, which is excluded from the repository:
  - decks, sources, keys and templates;
  - per-case results;
  - sample decks built on the owner's templates.
- **What is published.** Only aggregate figures, worded and shown to the owner first.

## The key

One row per number the tool reads in the old deck. The owner fills three columns:

| column | value |
|---|---|
| estado | desactualizada / vigente / sin fuente / ignorar |
| valor nuevo | the new value in the deck's own units and scale (only when desactualizada) |
| de dónde | optional: the file that gives it, or "calculado" |

The kit was checked end to end on a used synthetic case:
- the template;
- a key filled from that case's known answers;
- the seal;
- the score, which matched the scorer used since v2.2 exactly.

Numbers the tool does not read cannot be keyed: in a picture, or a chart that is an image. On that case
the template listed 107 of the 111 numbers the case's author had keyed.
