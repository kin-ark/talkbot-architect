---
name: wiz-checker
description: Validates WIZ.AI exported talkbot dialogue JSON files. Use when the user asks to check, validate, lint, or verify a WIZ.AI speech*.json file, or when reviewing such a file for structural and logical correctness.
---

# WIZ.AI Talkbot Checker

This skill validates a WIZ.AI exported dialogue JSON file and presents findings.
It does **not** modify the file.

## When to use this skill

Invoke when the user:
- Asks to validate, check, lint, or verify a WIZ.AI dialogue JSON.
- Pastes or references a `speech*.json` file in a validation context.
- Asks "are there any issues with this dialogue file?"

Do **not** invoke for:
- Editing or auto-fixing the JSON. The Checker is read-only. Fixes are the
  Modifier's job (a future skill).
- General WIZ.AI questions unrelated to a specific file.

## How to invoke

Run the CLI from a Bash tool call:

```bash
python .claude/skills/wiz-checker/scripts/check.py --json <absolute-path-to-file>
```

Parse the stdout as JSON. The shape is:

```json
{
  "file": "...",
  "summary": {"errors": N, "warnings": M, "checks_run": [...]},
  "findings": [
    {
      "code": "WIZ201",
      "severity": "error",
      "location": {"entity": "Utterance", "id": "...", "field": "text"},
      "message": "..."
    }
  ]
}
```

If `summary.errors > 0` or `summary.warnings > 0`, present findings to the user.
If the CLI exits with code 3, report a parse failure with the stderr text.

## How to present findings

1. **Lead with the headline counts.** Example: "Found **3 errors** and **2 warnings** in `speech1234.json`."
2. **Group findings by code prefix:** `WIZ0xx` (schema), `WIZ1xx` (graph),
   `WIZ2xx` (variables), `WIZ3xx` (intents). Surface errors before warnings within each group.
3. **For each finding, show:** `[code] [severity] [entity:id.field] — message`.
4. **Add context.** When a finding references a specific entity (e.g. Utterance
   `abc-uuid`), use the Read tool to fetch the relevant snippet from the source
   JSON file and show the offending text/structure.
5. **Offer to dive deeper.** End with: "Want me to walk through any specific
   finding in more detail, or check another file?"

## What this skill must NOT do

- **Do not auto-fix findings.** The Checker is strictly read-only. If the user
  asks for fixes, explain that the Modifier skill (not yet built) is the right
  tool, and offer to help draft the fix manually if asked.
- **Do not invent codes.** Only codes returned by the CLI are valid.
- **Do not run the CLI without a file path.** If the user has not specified a
  file, ask which file to check.

## Code reference

| Prefix     | Domain                                              |
|------------|-----------------------------------------------------|
| WIZ001–099 | Schema shape: required fields, enum membership.     |
| WIZ100–199 | Flow integrity: orphans, unreachable, dead-ends, cycles. |
| WIZ200–299 | Variable consistency: undeclared / unused.          |
| WIZ300–399 | Intent coverage: required intents, fallback intents.|

## Troubleshooting

- **Exit code 3 / parse error:** the file is unreadable, not valid JSON, or
  contains a malformed ID. Show the stderr message to the user.
- **No findings, but file looks suspicious:** the v1 check set is deterministic
  and conservative. Semantic checks (tone, coherence) are v2. Tell the user
  the file is structurally valid, and offer to scan it manually.
