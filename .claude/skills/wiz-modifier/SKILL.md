---
name: wiz-modifier
description: Modifies an existing WIZ.AI exported talkbot dialogue JSON (or export ZIP) by applying registry-defined transformations, and generates the T0–T12 import-test matrix. Use when the user asks to modify, edit, transform, or patch a WIZ.AI speech*.json/export, or to generate import-test files for debugging an import failure.
---

# wiz-modifier

Applies transformations to an existing WIZ.AI export. Two modes:

- **Free-form modification** — the user describes a change ("change the speechId", "rename the bot", "add a variable") against a `speech*.json` or export `.zip`.
- **Import-test matrix** — generate the T0–T12 bisection files from `docs/original-vs-builder-deep-comparison.md` 6 in one command.

## Chat protocol

1. **Identify the target.** Which file or ZIP? Confirm it exists. (Default baseline for import tests: `talkbot/Empty+Dialogue.zip` — a ZIP so the WAV is carried into T0–T10 and T11 tests the WAV's absence.)
2. **Interpret the request.** Map it to registry ops (see below). If it's "generate the import tests", use the preset. If nothing maps cleanly, use the `set-path`/`delete-path` escape hatch.
3. **Draft the mod-manifest** and show it inline.
4. **Confirm** with the user before applying.
5. **Apply.** Run the CLI:
   - Modification: `python .claude/skills/wiz-modifier/scripts/modify.py --mods <mods.yaml> [--force]`
   - Matrix: `python .claude/skills/wiz-modifier/scripts/modify.py --preset import-test-matrix --in <baseline.zip> --out talkbot/_import-tests/ [--force]`
6. **Report** the output path, what changed, and any advisory checker findings.

## Registry ops (Phase 1)

| Op | Params |
|----|--------|
| `set-speech-id` | `value: random\|<16-digit>` |
| `set-component-uuid` | `component`, `value: random\|<uuid>` |
| `set-bsc-name` | `component`, `value` |
| `set-bsc-id` | `component`, `value` |
| `add-bsc-keys` | `component`, optional `keys` |
| `populate-details` | `component`, `nodes: [{id,label,parent}]` |
| `add-component` | `name`, optional `nodes` |
| `add-variable` | `name`, optional `branch` |
| `add-intent` | `name`, `keywords`, `user_responses`, optional `branch`/`language` |
| `set-path` | `key`, `pointer: [...]`, `value`, optional `create` |
| `delete-path` | `key`, `pointer: [...]` |

## Knowledge-Base ops

A KB's Default Response = **Single Sentence** (`kdInfo` `answerType:1` answers) OR **Multi-Round** (an `answerType:2` delegate → component). `after` = "After The Answers": `wait` (afterSentence 0, default) | `hangup` (1).

| Op | Params | Notes |
|----|--------|-------|
| `add-kb` | `name`, `intents:[..]`, `answers:[..]`, optional `multi_round` | create; intents must be declared (else WIZ302) |
| `rename-kb` | `name`, `new_name` | dedup-guarded |
| `set-kb-intents` | `name`, `intents:[..]` | replace; each must exist in SpeechIntent |
| `add-kb-answer` | `name`, `text`, optional `after` | appends an answer + SCK row |
| `edit-kb-answer` | `name`, `new_text`, `old_text`\|`index`, optional `after` | **resets audio** (`sentenceTextUrl=""`) → re-synth on deploy; `after` omitted = unchanged |
| `remove-kb-answer` | `name`, `text`\|`index` | guards ≥1 response remains |
| `set-kb-multiround` | `name`, `target_component`\|`null` | set → target `category=2`; remove guards against emptying the KB; leave-old+warn |
| `delete-kb` | `name` | **user-created only** (`isInit=0`); **blocks** if a goto_kb node references it |

KB-edit ops route through a shared `KbEditor` (decode→mutate→flush, ids preserved). Checker side: `WIZ302` (intent declared), `WIZ303` (goto_kb → missing KB, WARNING+deploy-blocker, library-tolerant), `WIZ304` (user KB with no Default Response, WARNING+deploy-blocker, system KBs exempt). The 6 flow-mutation ops (`rewire-edge`, `delete-edge`, `delete-node`, `move-node`, `rename-node`, `complete-component`) live alongside these.

## Mod-manifest format

```yaml
input: talkbot/Empty+Dialogue/speech4010869963530658988.json
wav: talkbot/Empty+Dialogue/01735200078309635328.wav   # optional
mods:
  - op: set-bsc-name
    component: 0
    value: "1. Greeting"
output:
  path: talkbot/_import-tests/custom.zip
  format: zip          # zip | zip-no-wav | json
```

## Component-export mode

The modifier auto-detects a WIZ component-library export (`componentImportAndExportDTOS` envelope) on load. It adapts the component's DTO format to the full-export shape ops already understand, applies mutations unchanged, and writes the component envelope back (JSON only). Untouched passthrough fields (envelope `name`, per-entry metadata, entity/function/tag lists) are preserved verbatim.

A component is a standalone reusable unit; component-mode op restrictions forbid bot-scope operations:
- **Forbidden ops:** `add-kb`, `rename-kb`, `set-kb-intents`, `add-kb-answer`, `edit-kb-answer`, `remove-kb-answer`, `set-kb-multiround`, `delete-kb`, `set-hotwords` (all bot-level).
- **Forbidden node types:** `goto_kb`, `goto_mr`, `talk_continue` (all require bot context).

These ops raise `ValueError("component mode: ... unsupported")` before any mutation. Component input requesting ZIP output raises; JSON is the only valid output format.

## Notes

- The checker runs in **advisory** mode (findings printed, never blocks) — import-test files are deliberately divergent.
- Untouched top-level fields pass through byte-identical; the modifier is never a fidelity variable.
