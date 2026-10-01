# H01–H05: retired as blind evidence

These five public holdout cases were sealed in v1.2 and run once with frozen rules
(v1.2: 81.0, engine e3b63e1 — the last unbiased number, CHANGELOG 1.2.0). Their renders
were then inspected during v1.2 and v1.3, so they are **development-known** from v1.3 on.

They stay in the repository unchanged (files and `SEAL.json` hashes are not rewritten) and
can still be run as `cpe eval --suite holdout_v1` for historical continuity, but any number
they produce after v1.2 is development evidence, not validation. The current sealed holdout is
`evals/holdout/v2/`.
