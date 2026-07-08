---
name: wiz-builder
description: Scaffolds a new WIZ.AI talkbot dialogue JSON from a YAML manifest. Use when the user asks to create, build, or scaffold a new WIZ.AI talkbot from scratch.
---

# WIZ.AI Talkbot Builder

This skill produces a fresh, checker-clean WIZ.AI talkbot export from a small
human-readable manifest. The manifest captures the user's intent (name, language,
canvases, custom variables, custom intents); a Python compiler mutates a parsed
copy of the Empty+Dialogue baseline into the final `speech*.json`.

## WIZ terminology

WIZ.AI models most terminal/jump nodes as a single "Exit Node" with a "Next Step" setting; our internal `type` names are its variants. This table maps internal names to WIZ.AI platform terminology:

| Internal name (type) | WIZ.AI platform name |
|---|---|
| talk (type 1) | Talk Node |
| conditional (type 7) | Conditional Judgment Node |
| assign (type 10) | Variable Assignment Node |
| nested (type 11) | Nested Component Node |
| exit (type 2) | Exit Node (Next Step: Hang up) |
| transfer (type 13) | Transfer to Human Agent |
| goto_component (type 4) | Exit Node → Go to Component |
| goto_kb (type 8) | Exit Node → Go to Knowledge Base |
| goto_mr (type 9) | Exit Node → Go to specific multi-round dialogue |
| talk_continue (type 5) | Exit Node → Wait For User Response |
| exit_port | Exit Node → Component Exit (named return to the parent component) |
| component (category:1) | Component — Main Talk-Flow |
| component (category:2) | Multi-Round Dialogue |
| Knowledge Base | Knowledge Base |
| Intent | Intent |
| Tag | Tag (disposition/label) |
| Hot Words | Hot Words |
| Variable | Variable |
| speech*.json | Talkbot / Dialogue |

## When to use this skill

Invoke when the user:
- Asks to create, build, scaffold, or start a new WIZ.AI talkbot from scratch.
- Says things like "build a payment reminder bot" or "scaffold a new dialogue".

Do **not** invoke for:
- Validating an existing `speech*.json` (use `wiz-checker`).
- Modifying an existing talkbot (future Modifier skill).
- Building anything that needs utterances or audio links (out of scope for v1).

## Six-step chat protocol

1. **Gather requirements.** Through conversation, learn the bot's:
   - `name` (free-form, e.g., "Payment Reminder").
   - `language` (default `IDN`; ISO codes IDN/ENG/ZHO supported).
   - `branch` (default `dev`; `dev` or `prod`).
   - Canvases the user wants, with their names and the nodes inside (labels + parent structure).
   - Optional: custom variables and custom intents.

   Don't push for utterances or audio — those are out of scope for v1.

2. **Surface unknown labels.** If a node label isn't in
   `.claude/skills/wiz-builder/schema/known_node_labels.yaml` (Greeting, Pitch,
   Closing, Re-ask Limit, etc.), mention it to the user but don't reject — the
   manifest still compiles.

3. **Draft the manifest.** Write the YAML to a temp path (e.g.,
   `/tmp/wiz-builder-manifest-<random>.yaml`), then show it inline as a code
   block. Highlight unfamiliar labels.

4. **Confirm with the user.** Ask: *"Here's the manifest I'd compile. Want me
   to build, or should I adjust?"* Wait for explicit approval. Iterate on the
   manifest until the user is satisfied. Don't compile until they say so.

5. **Compile.** Save the manifest to `talkbot/<slug>/manifest.yaml`, then run:

   ```bash
   python .claude/skills/wiz-builder/scripts/build.py \
     --manifest talkbot/<slug>/manifest.yaml
   ```

   By default, `--emit full` produces a complete bot export. To emit a **component-library export** instead, pass `--emit component`:

   ```bash
   python .claude/skills/wiz-builder/scripts/build.py \
     --manifest talkbot/<slug>/manifest.yaml --emit component \
     --out talkbot/<slug>/component.json
   ```

   Component mode compiles each canvas into a reusable component (`componentImportAndExportDTOS` envelope). Bot-level features—`knowledge_bases`, `hot_words`, and node types `goto_kb` (WIZ: Exit Node → Go to Knowledge Base) / `goto_mr` (WIZ: Exit Node → Go to specific multi-round dialogue) / `talk_continue` (WIZ: Exit Node → Wait For User Response)—are unsupported in component mode; the builder will reject them with a clear error.

   The CLI prints a JSON result:
   ```json
   {
     "output": "talkbot/<slug>/speech<id>.json",
     "errors": 0,
     "warnings": N,
     "codes": {"WIZ202": N, ...}
   }
   ```

6. **Report.** Summarize the result:
   - "Built clean — see `<output>`" when warnings == 0.
   - "Built with N warnings — codes: {…}" when warnings > 0; explain that warnings
     usually mean unused custom variables (will resolve once the user adds
     utterances in WIZ.AI) or expected empty-canvas state.

## What this skill must NOT do

- **Skip the confirm step (4).** The manifest preview is the user's audit window.
  Always show the manifest and wait for approval.
- **Author utterances or `SpeechAudio` links.** Out of scope; defer to a future
  Modifier skill. Politely tell the user they'll add these in the WIZ.AI UI after
  importing.
- **Emit Component Library / orphan-parent references.** All `parent` values
  must resolve within the same canvas. Cross-canvas refs are also rejected by
  the manifest schema.
- **Overwrite an existing `talkbot/<slug>/` directory** without explicit user
  confirmation. The CLI requires `--force` for non-empty output directories;
  surface the warning and ask before retrying.

## Tags (dispositions)

Author the WIZ `SpeechTag` disposition vocabulary and assign tags to nodes:

- Top-level `tags:` — a list of categories: `{name, values: [labels], is_mutex?: bool, type?: 0|3}` (0 = enumerated, 3 = free-text). Emits the `SpeechTag` table.
- Top-level `enterprise_id:` — optional; sets `entId` on every tag (match your WIZ tenant so it deploys correctly). Omitted → a deterministic id is minted.
- Node-level `tags:` — `[{category, values: [subset]}]` assigns dispositions to a node; emits a denormalized `data.tag_list` (category header + selected value rows). `kbTag` is auto-derived from all node assignments.

Output is checker-clean (sub-project-1 `WIZ401`/`WIZ402` resolve by construction). A node assigning an undeclared category or an unknown value is a `CompileError`. Tags are bot-scope — `--emit component` rejects `tags:` and node `tags:`. (KB-level tag assignment + modifier tag ops are separate later sub-projects; the from-scratch tag deploy shape has a pending human import/deploy gate.)

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success (possibly with warnings) |
| 2 | Manifest error (parse or schema violation) |
| 3 | Output path conflict (directory non-empty; `--force` not given) |
| 4 | Internal compiler error (bug; includes traceback) |
| 5 | Checker rejected output (compiler bug; output deleted) |

If you see exit 2, fix the manifest. Exit 3 → ask the user about `--force`.
Exit 4 or 5 → surface the error to the user and stop; these indicate bugs in
the compiler, not in their input.

## Spec reference

`docs/superpowers/specs/2026-05-21-wiz-builder-design.md`
