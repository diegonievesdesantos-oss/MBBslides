# s1 — expert feedback (storyline A/B, blind)

One expert evaluator (owner, ex-McKinsey; expert single-rater standard), 4 development cases,
4 decisive votes: **2–2**. Self-consistency on repeated pairs 2/2. The key was revealed after voting.

| pair | case | preferred |
|---|---|---|
| p001 | churn_es | B — agent + protocol 1.0 |
| p002 | margin_recovery | B — agent + protocol 1.0 |
| p003 | plant_capacity_es | A — agent, no protocol |
| p004 | promo_effectiveness | A — agent, no protocol |

## Written feedback (the evaluator's words, translated)

The evaluator saw strengths in each version, without knowing which was which.

**Version 1: numeric discipline.**
- The figures reconcile with each other, and it says openly what is still missing to reach the target.
- It quantifies each lever and each argument separately, so all of it can be defended to a CFO.
- It designs the governance: validation gates, approval criteria and tracking KPIs.
- The storyline stands on its own with data, without needing to see the deck.
- It is precise in its claims and does not exaggerate what the data says.

**Version 2: thinking about the decision.**
- It challenges the plan or budget in force and shows why it does not hold.
- It uses the data to compare alternatives (what each option costs), not only to describe the situation.
- It manages uncertainty: it marks which figures are upper bounds and what has to be validated before committing.
- It closes the decision with concrete proposals that can be approved, not with assignments for later.
- It orders the narrative better: first the problem or risk, then the solution.

## Mapping (read after unblinding, from the storylines)

- **Version 1 is B (protocol 1.0).** In margin_recovery it says "≈1.4 pp identified vs the 1.5 pp target",
  splits the levers 0.9 / 0.3 / 0.2 and gates the repricing on a Q1 2027 price test.
- **Version 2 is A (baseline).** In margin_recovery it says "the €17M is an upper bound that assumes no volume
  loss … validate within 60 days".
  - In promo_effectiveness it closes with an approval criterion for every event, where B closes with
    "commission a gross-margin bridge … before sign-off".
  - In plant_capacity_es B ends with "estimate the cost of the programme", which is an assignment, not a decision.

So the protocol produced the disciplined, traceable storyline, and it lost where the close was not a decision.
**Protocol 1.1 adds a decision frame (`storyline.json["decision"]`)** that asks for both sets of strengths.
Each strength becomes a check (docs/REASONING_PROTOCOL.md):

| strength | check |
|---|---|
| figures reconcile; the gap to the target is stated | levers sum to `identified` (ARITHMETIC_ERROR, hard); `gap` = target − identified (hard); GAP_NOT_STATED |
| each lever quantified and defensible | LEVER_UNQUANTIFIED; each impact grounded in the facts it cites (UNSUPPORTED_NUMBER, hard) |
| governance | GATES_MISSING, KPIS_MISSING |
| stands alone with data | KEYLINE_WITHOUT_NUMBERS (info) |
| no exaggeration | OVERCLAIM_BOUND (an upper bound stated as certain in the governing thought) |
| challenges the current plan | CURRENT_PLAN_NOT_TESTED, CURRENT_PLAN_UNSUPPORTED |
| compares options on cost | OPTIONS_NOT_COMPARED, OPTION_UNCOSTED |
| marks upper bounds and what to validate | UNCERTAINTY_UNMARKED (upper bound / assumption without `validate`) |
| approvable close | ASK_MISSING, ASK_DEFERRED (only `commission`-type asks) |
| problem before solution | SOLUTION_BEFORE_PROBLEM (key-line roles) |

**Status: development data.** These votes and this feedback shaped protocol 1.1. Whether 1.1 is better
needs a new storyline round on cases it has not seen.
