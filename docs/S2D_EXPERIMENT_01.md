# Source-to-deck experiment 01 — does the reasoning protocol change the storyline?

**Date** 2026-10-01 · **Status** development (cases written by the developing agent) · **Human
verdict pending** (round s1).

## Design

Four development cases (`evals/source_to_deck/development/`): margin recovery (EN, CSV + notes),
customer churn (ES, multi-sheet Excel + notes), promotion effectiveness (EN, PDF + DOCX table +
memo), plant capacity (ES, PDF + DOCX table + email). Each has a brief, critical facts, required
conclusions and traps (a management explanation contradicted by the data, a forecast posing as an
actual, an investment that is not needed…).

Two systems, each an independent agent with a fresh context, given only its copy of the brief and
the sources (isolation instructed, not technically enforced):

- **A — baseline:** brief + sources → storyline in a fixed template.
- **B — protocol 1.0:** brief + sources + docs/REASONING_PROTOCOL.md + `cpe reason facts/check`,
  iterating until the check passed → artifacts + the same storyline template.

Runs are stored in `runs/baseline_agent_01/` and `runs/protocol_agent_01/` of each case.

## Automatic results (`cpe reason eval-text`, same yardstick for both)

| case | conclusions A / B | traps A / B | untraced numbers A / B |
|---|---|---|---|
| margin recovery | 3/3 · 3/3 | 0 · 0 | 5 of 65 · 3 of 36 |
| churn (ES) | 3/3 · 3/3 | 0 · 0 | 3 of 36 · 2 of 15 |
| promotions | 3/3 · 3/3 | 0 · 0 | 0 of 37 · 0 of 28 |
| plant capacity (ES) | 3/3 · 3/3 | 0 · 0 | 6 of 42 · 3 of 31 |

B also passes the full benchmark (`cpe reason eval`): factuality PASS, critical-fact recall 1.0,
every stopping criterion met, critic findings recorded for all five roles.

## Reading

- **Substance is a tie.** Both systems reach every required conclusion and fall into no trap. These
  cases are too easy for a strong model; they cannot show a reasoning gain. Harder cases are
  needed: conflicting sources, buried drivers, several plausible answers, longer and messier
  inputs — and cases written by someone else.
- **What the protocol measurably adds is verifiability, not insight:** every number B states is
  either a source fact or a formula that is recomputed; A states more numbers that cannot be
  traced to one operation on the sources (gross-profit levels, multi-step capacity arithmetic).
  B's "untraced" numbers are its own verified computed facts.
- **B wrote fewer numbers** (110 vs 180 in total), and in two cases fewer slides than allowed.
- **Whether B's storylines are better or worse for a client is a human judgement** — the blind
  round `s1` asks exactly that.

## Evaluator fixes found by this experiment

The text evaluator raised false traps that a reader would not: negated claims ("volume is not the
problem", "the lines are not at full capacity"), claims reported in order to refute them
("Marketing's plan would raise the budget…") and co-occurring terms far apart in a long sentence.
It now requires terms within 60 characters, affirmed (no negation before, after or on a term) and
not reported. Term-based trap detection remains a heuristic; the human verdict decides.

## Protocol feedback from the agents

The B agents had to learn several formats from the check's errors (computed-fact shape, numeric
confidence, one key-line id per slide, `refutes` for rejected hypotheses, `rationale`). They are
now documented in docs/REASONING_PROTOCOL.md ("Exact formats"); the hypothesis-tension note reads
`rationale`; "100 EUR" is money.
