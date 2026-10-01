"""Source-to-deck reasoning artifacts (v1.7).

The agent is the thinking layer; this package makes its thinking OBSERVABLE and TESTABLE. Every
stage of the chain writes a structured artifact into a project's `work/` folder, and every artifact
has a deterministic validator:

    sources/ ─► source_manifest.json   what was read (hashes)                      cpe reason facts
             ─► facts.json             atomic, traceable facts (+ derived facts)   cpe reason facts
    project.json                       business question object (audience, decision, question, …)
    hypotheses.json                    candidate explanations, tested against facts (agent)
    insights.json                      reasoning across facts, grounded (agent)
    storyline.json                     candidate governing thoughts, chosen answer, key line,
                                       decision frame (agent; decision.py, protocol 1.1)
    deck_plan.json                     slide architecture: why each slide exists (agent)
    ghost_deck.md                      the argument from headlines alone        cpe reason ghost
    deck.json                          the render spec (evidence items cite fact ids)
    reasoning_report.json/.md          every check, hard gates, stopping criteria cpe reason check

    cpe reason trace <work> "<sentence>"   why is this sentence in the deck? → lineage to sources

The engine never invents content: facts come from sources, everything above facts is written by
the agent and checked here. Hard factuality failures block the deck (reasoning_report: blocked).
Protocol and critic roles: docs/REASONING_PROTOCOL.md. The protocol version is recorded in every
artifact the tools write, so a source-to-deck result is reproducible as engine + protocol + model.
"""
PROTOCOL_VERSION = "1.1"
ARTIFACTS = ("project.json", "source_manifest.json", "facts.json", "hypotheses.json", "insights.json", "storyline.json", "deck_plan.json", "deck.json")
