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

## Messy inputs, binding and new exhibits (v1.8)

| where | spec | what it does |
|---|---|---|
| evidence item | `{"fact": "F0012", "at": "visual.rows[1][2]"}` (or a list of paths) | binds the fact to that table cell or chart point. A different value there is a hard `CELL_MISBOUND`, a missing path is `BINDING_PATH_MISSING`. Chart points: `visual.data.series[0].values[3]`; waterfall steps: `visual.data.steps[2].value` |
| table cell | `"n/a"`, `"n/d"`, `"no disponible"` or `{"value": null, "na": true}` | explicit missing data: printed `n/a` (`n/d` in Spanish, `n.d.` in French/Italian, `k.A.` in German), never 0; the column stays numeric |
| chart value | `"n/a"` in `series[].values` | a gap in the series, labelled `n/a` / `n/d` at the baseline, so it never reads as zero (`series[].na` lists the indices after normalisation) |
| exhibit | `{"type": "cause_effect", "data": {"causes": [{"label", "detail", "value", "emphasis", "link"}], "effect": {"label", "value"}, "consequences": [{"label", "detail"}]}}` | causes → effect → consequences; the arrows mean "causes", not "comes next"; `link` labels the mechanism on the arrow. Message type `causality`. Alias `causal_chain` |
| layout | `timeline_decisions` (family 08_timeline) | a slide with a `timeline` (or `gantt`) as `visual` and a decisions table in `exhibits`: the dated gates across the top, the decisions (owner, date, impact) below |

Without a binding, a cell is still checked by its labels: when its value belongs to a cited fact that
does not mention the row, while another cited fact names the row and the column, `CELL_MISBOUND` is a
warning ("probably swapped").

Existing decks: `cpe deck ingest old.pptx -o work` writes `old_deck.json` (per slide: role, layout,
headline, body, exhibits with their data, every number with its location), `old_deck_spec.json`
(a starting deck.json that rebuilds charts and tables natively, waterfalls included) and
`old_ghost.md`. After `cpe reason facts` on the new sources, `cpe deck stale work` classifies each
old number as current, outdated (with the new value and its fact) or untraced, and each slide as
keep / update / review (`update_plan.json`, `update_plan.md`).

Since 1.9, a number is matched on its own words, not on its value:
- its measure, phase, zone and year, and its unit;
- page numbers, document codes and phase indices are `ignored`;
- restatements of the old plan (budget, offer, business case) never confirm a number.

The original file can then be updated in place:
- `cpe deck edits work` writes `edits.json` / `edits.md`. It proposes one edit per outdated number,
  written in the old number's notation ("3,2" M€ → "4,03"). Every edit starts as `approved: false`.
- `cpe deck patch old.pptx work/edits.json -o new.pptx [--mark]` applies only approved edits to the
  original pptx and leaves everything else untouched.
  - Numbers keep their run formatting. Table cells are edited in place. Chart points go through the
    chart's own data.
  - Other operations: `replace_text`, `set_chart`, `delete_slide`, `note`.
  - Each change is written to the slide's notes. `--mark` highlights the new text.
  - An edit not found where the plan says is reported, never applied elsewhere (`patch_report.md`).

Since 2.0:
- `cpe update old.pptx sources/ -o work` runs ingest, facts, stale and edits in one go.
- `cpe update --apply work -o new.pptx [--mark] [--accept-derived]` patches the original file.
- Derived figures (totals, net rows, ratios, sums in a sentence, the same figure repeated) are
  recomputed from approved values. `cpe deck edits work --derive` shows them before applying.
- `work/messages.md` says whether each headline still holds with the new values (threshold claims).
  Edit ops `set_headline {slide, text}` (keeps the headline's formatting) and
  `replace_slide {slide, from, index}` (transplants a built slide onto the old slide's layout).
- `cpe update --rebuild work [--slides N,M]` builds the slides whose message no longer holds, in the
  old deck's style.

## Patches

`{"op": "set" | "delete" | "append", "slide": "s07", "path": "visual.data.series[0].values", "value": …}`,
`{"op": "insert_slide_after", "slide": "s06", "value": {slide}}`, `{"op": "remove_slide", "slide": "s09"}`,
`{"op": "move_slide", "slide": "s09", "after": "s03"}`. Omit `slide` to patch the spec root
(e.g. `{"op": "set", "path": "meta.theme", "value": "graphite"}`).
