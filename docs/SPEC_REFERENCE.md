# Deck spec reference

The deck spec (`deck.json`) is the contract between thinking and rendering. Keys starting
with `_` are written by the engine (plan traces, autofix markers) and can be ignored.

```jsonc
{
  "meta": {
    "title": "…", "subtitle": "…", "client": "…", "date": "…",
    "deck_type": "strategy_deck",          // one of the 14 deck types → default profile
    "profile": "board",                     // optional override: board | standard | analytical | status
    "theme": "meridian",                    // meridian | graphite | harbor
    "confidentiality": "Strictly confidential",  // printed next to the page number
    "auto_split": true                      // mechanical table split fallback
  },
  "storyline": {
    "framework": "SCR",                     // SCR CII PDS DRI MPO CGT HEC
    "audience": "…", "decision_sought": "…",
    "governing_thought": "one-sentence answer",
    "key_line": [{"id": "K1", "role": "situation", "message": "…"}]
  },
  "slides": [ … ],
  "qa_exemptions": [{"slide": "s07", "code": "HEADLINE_UNQUANTIFIED", "reason": "qualitative slide"}]
}
```

## Slide fields

| field | kinds | meaning |
|---|---|---|
| `id` | all | unique id (patches target it) |
| `kind` | all | `cover` `agenda` `divider` `exec_summary` `content` (default) `statement` `closing` `appendix_divider` |
| `section` | content | key-line id the slide proves |
| `tracker` | content | small section label above the headline |
| `purpose` | content, exec_summary | what the audience must accept after the slide (required) |
| `headline` | content, exec_summary | the conclusion (required) |
| `subheadline` | content | optional one-line qualifier |
| `supporting_message` | content | the second-level message (goes to speaker notes) |
| `message_type` | content | drives visual reasoning (see VISUAL_GUIDE) |
| `evidence` | content | `[{claim, value?, values?, source?}]` — what proves the headline; numbers feed the headline check |
| `visual` / `exhibits` | content | the exhibit(s); `type: auto` lets the engine choose |
| `commentary` | content | `{title?, points: [...]}` so-what bullets |
| `kpis` | content | `{items: [...]}` KPI strip |
| `columns` | content | comparison / phase columns |
| `takeaway` | content | one-line so-what bar at the bottom |
| `layout` | content | `auto` (default) or a layout id |
| `source`, `footnotes` | content | required source on data slides |
| `notes` | all | speaker notes (default: purpose + supporting message) |
| `title`, `subtitle`, `number` | cover, divider | |
| `items`, `current` | agenda | agenda entries (default: divider titles) and the highlighted one |
| `text`, `support`, `style`, `attribution` | statement | |
| `reading_first` | content | prefer commentary-left layouts |

## Estimates, bounds and targets (v1.8)

A decision deck mixes actuals with estimates and upper bounds. Mark them on the number itself, never
only in a footnote:

| where | spec | renders |
|---|---|---|
| waterfall step | `{"label": "10 AEs", "value": 1.5, "estimate": true}` or `"bound": "upper|lower|range|estimate"` | hollow bar with a dashed outline; label `~1.5`, `≤2.5`, `≥…` |
| waterfall | `"target": {"value": 5.6, "label": "Needed"}` | dashed reference line with its label (no fake total bar) |
| waterfall | `"delta_colors": "muted"` + `"highlight": ["Onboarding"]` | every step grey except the highlighted one; automatic labels in text colour |
| waterfall | `"proof_label": false` | no automatic "Δ vs start" label |
| table cell | `{"value": 2.0, "bound": "estimate"}` | stays a right-aligned number in the column format, printed `~2.0` / `≤4.5` |
| table column | `"width": 2.2` | fixed width in inches; columns without a width share the rest |

Every number on a slide, these included, must be grounded in the slide's cited facts
(`cpe reason check`, docs/REASONING_PROTOCOL.md).

## Patches

`{"op": "set" | "delete" | "append", "slide": "s07", "path": "visual.data.series[0].values", "value": …}`,
`{"op": "insert_slide_after", "slide": "s06", "value": {slide}}`, `{"op": "remove_slide", "slide": "s09"}`,
`{"op": "move_slide", "slide": "s09", "after": "s03"}`. Omit `slide` to patch the spec root
(e.g. `{"op": "set", "path": "meta.theme", "value": "graphite"}`).
