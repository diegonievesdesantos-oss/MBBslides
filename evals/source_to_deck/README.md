# Source-to-deck benchmark

Does MBBslides build the RIGHT deck from raw material? Each case gives raw `sources/`, a brief
(`project.json`) and a `reference.json` with what a good answer must contain — critical facts,
required conclusions, known traps — never a deck to match word for word (docs/SOURCE_TO_DECK.md).

| set | status | rule |
|---|---|---|
| `development/` | **development** — visible, tunable | written by the developing agent; for building and debugging the reasoning layer |
| `sealed/` | empty | cases written before a cycle, not used in it; run once at the cycle's freeze |
| `external/` | **AWAITING EXTERNAL INPUT** | cases written outside the development loop (docs/EXTERNAL_HOLDOUT_PROTOCOL.md) |

```bash
scripts/cpe reason facts <case>/sources -o <work>          # fact model (deterministic)
# … the agent writes hypotheses / insights / storyline / deck_plan / deck.json (docs/REASONING_PROTOCOL.md)
scripts/cpe reason check <work>                            # every artifact + hard factuality gates
scripts/cpe reason eval <case> <work> --model … --skill …  # benchmark dimensions, reported separately
```
