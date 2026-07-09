# WIZ.AI General Bot Authoring Playbook

A domain-agnostic guide to authoring a mature, production-grade WIZ.AI dialogue bot. Follow the universal flow skeleton and the maturity bar to ensure your bot imports cleanly and deploys reliably.

## Universal Flow Skeleton

Every mature bot follows a linear progression:

```
Greeting + Identity Confirm (talk)
  ↓ branches: Correct → Continue / Wrong → Error handling / Unclassified
Information Collection (talk)
  ↓ branches: Proceed / Cannot Proceed / Unclassified
Route/Resolve (talk / conditional / nested)
  ↓ branches: Success / Failure / Unclassified
Closing (exit or transfer)
```

Each component must end in a **terminal node** (exit or transfer). All talk nodes branch on **Positive** / **Negative** / **Unclassified** (or locally renamed variants). Use `goto_kb` to handle off-script user intents at any stage.

## The Maturity Bar

**Must-haves** for a bot that imports and deploys cleanly:

1. **Every component ends in an Exit or Transfer.** Components without a terminal node fail import (`WIZ107`).
2. **Every talk node has a connected "Unclassified" branch.** This catch-all handles parse failures, hesitations, and off-topic input (`WIZ108`). It must route somewhere (usually to an Exit or a KB).
3. **Declare intents before KBs that trigger on them.** Call `add_intent` (with keywords and example user responses) BEFORE any KB that triggers on that intent.
4. **Assign a variable before a conditional reads it.** Use an `assign` node to set a value before a `conditional` node branches on it.
5. **IDN language only.** (`node_language: "3"`)
6. **Use only supported node types.** See the node glossary below.

## Node Types and When to Use Them

| Node type | Purpose | When to use | Terminal? |
|---|---|---|---|
| **talk** | Ask a question, provide information, branches on user intent | Default node for dialogue; use **2-3 rotation variants** (separated by `/`) for naturalness | No |
| **conditional** | Route based on a variable value | Decision points (e.g., Gender→Salutation, Company→Greeting, Date Collected→Today). Always include a `Default` fallback branch. | No |
| **assign** | Set a variable to a static value or computed result | Store form data, set salutation/greeting, track counters (e.g., convincer tier). One `Default` out-port. | No |
| **exit** | End the call cleanly (hangup) | Terminal path; speak closing text (e.g., "Thank you for calling"). Must exist in every component. | Yes |
| **transfer** | Escalate to a human agent | Speak a hand-off message, end the flow. Rarely used; prefer exit + spoken callback promise. | Yes |
| **goto** | Jump to another component (cross-component link) | Navigate between main flow components; rarely needed if components are linear. | Yes |
| **goto_kb** | Delegate to a Knowledge Base (intent-triggered response library) | Handle expected off-script intents: "How do I pay?", "What's the deadline?", "I already paid." Triggered by intent name. | Yes |
| **goto_mr** | Jump to a multi-round dialogue component | Advanced: hop between multi-turn sub-dialogues (only inside multi-round components). | Yes |
| **talk_continue** | Speak, then wait for user's next turn, no immediate branch | Only inside multi-round components; used in KB multi-round delegates; optionally returns to main flow via `config.target`. | Yes |
| **conditional (inside multi-round)** | Route inside a multi-round sub-dialogue | Same as conditional above; used in multi-round KB delegates or nested components. | No |
| **nested** | Delegate to a child component (reusable subflow) | Encapsulate repeatable subflows (collect payment method, verify identity, compute days between). Its out-ports mirror the child's `exit_port` nodes. | No |
| **exit_port** | Named return point from a child component | Only valid inside child components; each `exit_port` becomes an out-port on the parent's `nested` node. | Yes |

## Key Notes

- **Node positions auto-layout.** You do not specify (x, y) coordinates; the layout engine positions them based on the graph structure.
- **Knowledge Bases (KBs) extend intent coverage.** Author KBs only AFTER intents are declared. Each KB specifies triggering intents and an answer (single-sentence or multi-round sub-dialogue).
- **Intents drive NLU.** User-created intents must have keywords (comma-separated) and example user-responses (semicolon-separated) to signal the NLU engine what inputs map to that intent.
- **Branch consistency.** Use the same branch names across a component (e.g., always "Positive" / "Negative" / "Unclassified") so routing logic is predictable.
- **Rotation variants** (`/`-separated text in a node) are essential for sounding human. Always author 2-3 variants for talk nodes.
- **IDN-only:** The engine currently supports Indonesian (`node_language: "3"`) exclusively. Other languages are deferred.

## Disposition Tags for Call Outcomes

Track call outcomes (e.g., PTP, Refused, Wrong Number, Already Paid) by tagging terminal and branch nodes with **disposition tags**. Declare a `Disposition` tag category and its values at the manifest level; then tag each closing node with the appropriate outcome:

```yaml
tags:
  - name: Disposition
    values: [PTP, Refused, WrongNumber, AlreadyPaid]

# Tag a closing node with the outcome it represents:
  - {id: close_pos, type: exit, prompt: "Thank you for calling.", tags: [{category: Disposition, values: [PTP]}]}
```

Declare the category once at top level, then tag each terminal or branch node with its outcome. Both `scaffold_bot` (typed `tags` parameter) and `build` (manifest YAML) support disposition tags.

## Common Gotchas

- **Missing Exit = import failure.** `WIZ107` warns, `--deploy` gate blocks.
- **Unconnected talk branches = deploy risk.** `WIZ108` warns. Every talk node's output branches must route to another node or a KB.
- **Variable assigned after conditional reads it = silent deploy failure.** The conditional can only branch on a value set by an earlier assign node or a system/collected variable.
- **Intent not declared before KB trigger = intent mismatch.** Declare intents first, then author KBs.
- **transfer (type 13) has zero corpus use.** Use exit + a spoken callback promise instead.

---

For domain-specific guidance (intent taxonomy, script archetypes, KB patterns), see the vertical-specific playbooks (e.g., `debt_collection` for collections bots).
