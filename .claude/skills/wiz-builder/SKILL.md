---
name: wiz-builder
description: Scaffolds a new WIZ.AI talkbot dialogue JSON from a YAML manifest. Use when the user asks to create, build, or scaffold a new WIZ.AI talkbot from scratch.
---

# WIZ.AI Talkbot Builder

This skill produces a fresh, checker-clean WIZ.AI talkbot export from a small
human-readable manifest. The manifest captures the user's intent (name, language,
canvases, custom variables, custom intents); a Python compiler mutates a parsed
copy of the Empty+Dialogue baseline into the final `speech*.json`.

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

   Component mode compiles each canvas into a reusable component (`componentImportAndExportDTOS` envelope). Bot-level features—`knowledge_bases`, `hot_words`, and node types `goto_kb`/`goto_mr`/`talk_continue`—are unsupported in component mode; the builder will reject them with a clear error.

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
