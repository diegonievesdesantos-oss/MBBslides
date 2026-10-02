# Parallel Wording Guarantee (v3.1)

`src/cpe/editorial/parallel.py`, `signatures.py`. Elements of the same logical category are written as one
family. The guarantee works on groups, never on the whole deck.

## Groups

| kind | where | mandatory | strictness |
|---|---|---|---|
| explicit | `parallel_group` on a slide (or `editorial.parallel_group`), a key-line point, an exhibit or an item | yes | exact (declarative groups: family unless `target_signature` is set) |
| structural | process / value-chain / journey steps · gantt / roadmap rows · harvey-table option columns · operating-model pillars · cards on recommendation / design-principle / initiative / objective slides | yes | exact |
| structural | executive-summary statements · key-line arguments | yes | family (declarative conclusions, spec §57) |
| inferred | consecutive content slides of one section with the same explicit proposition role and claim type | no (advisory) | family |

An SCR executive summary (Situation / Complication / Resolution) is not a sibling group: its statements
play different roles. Different narrative roles (diagnosis → implication → recommendation) are never
grouped (spec §106).

## Signatures (English and Spanish)

`VERB_OBJECT_OUTCOME` (Consolidate suppliers to reduce complexity · Consolidar proveedores para reducir
complejidad) · `VERB_OBJECT` (Minimise upfront cost) · `ACTION_TO_OUTCOME` (Repricing electronics can recover
~1.4 pp · Repreciar electrónica permitiría recuperar…) · `SUBJECT_CHANGE_MAGNITUDE` · `DRIVER_EXPLAINS_OUTCOME`
· `CONDITION_IMPLIES_CONSEQUENCE` · `CLAUSE_SUBJECT_VERB_OUTCOME` · `GERUND_PHRASE` · `NOUN_PHRASE`.

Families: action (instructions: English imperative, Spanish infinitive) · declarative (conclusions) ·
gerund · noun. Nominal gerunds ("Pricing & promo reset") are labels among labels.

## Checks

| code | hard in a mandatory group when | otherwise |
|---|---|---|
| `PARALLEL_SIGNATURE_MISMATCH` | a member is of another family; same family, different shape in an explicit group | warning |
| `PARALLEL_ROLE_MISMATCH` | members declare different roles (or not the group's `parallel_role`) | warning |
| `PARALLEL_TENSE_MISMATCH` | instructions in mixed forms ("Collected the data" among imperatives) | warning |
| `PARALLEL_VOICE_MISMATCH` | explicit exact group mixing active and passive | warning |
| `PARALLEL_GRANULARITY_MISMATCH` | explicit group mixing a quantified outcome posing as an action ("Increase EBITDA by €12m") or a whole function ("Automate finance") with specific actions | warning |
| `PARALLEL_LENGTH_OUTLIER`, `PARALLEL_PUNCTUATION_MISMATCH`, `PARALLEL_NUMBERING_MISMATCH`, `PARALLEL_CAPITALIZATION_MISMATCH` | — | warning |
| `PARALLEL_REPEATED_OPENING`, `PARALLEL_GENERIC_VERB` | — | advisory (parallel ≠ repetitive, spec §62) |

In `standard` mode hard findings are warnings; in `legacy` everything is advisory.

## Meaning above symmetry

The guarantee never rewrites a member: it names the members that break the family and the target
signature, and the author (or agent) rewrites them. Priority: factual truth → proposition fidelity →
logical structure → parallel wording → style.

Not implemented: comparing the use of qualifiers across members ("up to", "at least") — listed in the
spec (§25) and left out because a lexical check would mostly flag legitimate differences.
