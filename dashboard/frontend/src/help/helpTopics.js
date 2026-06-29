// Bundled help content rendered by DocumentationPage. Plain markdown strings.
import {
  Rocket, PanelsTopLeft, Bot, Workflow, BookOpen, ShieldCheck,
  MousePointerClick, Download, GitBranch, MessagesSquare, KeyRound,
} from 'lucide-react';

export const helpTopics = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: Rocket,
    body: `## Getting Started

Talkbot Architect helps you read, build, validate, and edit **WIZ.AI dialogue exports** (the \`speech*.json\` files you import into the WIZ.AI platform) — without hand-editing raw JSON.

### Three ways to begin

1. **Upload** an existing export — a \`speech*.json\` file or a \`.zip\` (JSON + audio). Drop it on the upload zone or click to browse.
2. **Start from scratch** — open a blank canvas and describe the bot you want in Chat (e.g. *"make me a Debt Collector talkbot"*).
3. **Try a sample** — load one of the bundled, validated starter bots and edit from there.

### The layout

- **Top bar** — the bot's name (click to rename), **Undo** / **Redo**, and **Export**.
- **Left rail** — your **sessions**, plus footer buttons for Statistics, this Documentation, Settings, and the light/dark toggle.
- **Center** — the **flow graph** of your bot (or the start screen when nothing is loaded).
- **Right dock** — tabs for **Chat**, **Findings**, **Properties**, **KB**, and **Components**.

@@fig:layout@@

### How editing works

Every change the agent makes is a **proposal** — you see a diff and how it affects the validation findings *before* anything is applied. Review it, then **Apply** (or reject). Applied changes are **undoable**. Your work is saved automatically as a session.`,
  },
  {
    id: 'sessions',
    title: 'Sessions & the rail',
    icon: PanelsTopLeft,
    body: `## Sessions & the rail

Each bot you work on is a **session** — its own document, chat history, undo stack, and token usage. Sessions live in the left rail.

- **New** (the **+** at the top of the rail) returns you to the start screen to begin a fresh bot. Your current session stays in the list.
- **Switch** — click any session to load it.
- **Rename** — hover a session and click the pencil (this is the *session label*; the bot's own name is set separately in the top bar).
- **Delete** — hover and click the trash icon (asks for confirmation).
- **Collapse** — the panel toggle narrows the rail to icons; the expand button is highlighted while collapsed so you can find it.

### Rail footer

- **Statistics** — token usage (input / output / turns) and model, for the active session and across all sessions.
- **Documentation** — this help.
- **Settings** — AI provider, model, and API key.
- **Theme** — toggle light / dark.

Sessions and your active selection are remembered across reloads.`,
  },
  {
    id: 'agent',
    title: 'What the agent can do',
    icon: Bot,
    body: `## What the agent can do

The Chat agent operates on the **single export in the active session**. It works in tools, and **every edit tool is dry-run**: it returns a diff plus a checker delta as a **proposal**. Nothing changes until you **Apply**; **Undo** / **Redo** step through applied changes.

@@fig:proposal-flow@@

### Read / understand
- **Validate** the export and **summarize** the flow.
- **Read a node** to inspect its details.
- **Get facts** (WIZ.AI enums, defaults, intents, languages) and **get the manifest schema** — the agent consults these before building.

### Build new
- **Scaffold a bot** — multi-canvas, with variables, intents, node types, and edges, from structured parameters.
- **Build from a manifest** — full engine power via a raw YAML manifest.

### Edit an existing bot
- **Add** components, nodes, intents, and variables.
- **Connect components** — a one-call cross-component jump.

### Reshape the flow (in-place mutation)
- **Rewire** an edge, **delete** an edge or a node, **move** a node to another component, **rename** a node, and **auto-complete** a component to the completeness rules.

### Escape hatches
- **Apply raw modifier ops** (reaches every operation the engine supports) and **set / delete a JSON path** for anything not covered by a dedicated tool.

### Best-practice guardrail

When a proposed change would leave **error-level** findings, the agent sees them and tries to fix them before handing the result to you — so proposals tend to arrive checker-clean.`,
  },
  {
    id: 'node-types',
    title: 'Node types & limits',
    icon: Workflow,
    body: `## Node types & limits

**Nine** node types are supported:

| Type | What it does |
|---|---|
| **talk** | Speaks a prompt and branches on the caller's reply. |
| **exit** | Ends the call (hang up). |
| **transfer** | Hands the call to a human agent. |
| **goto** | Jumps to another component by name. |
| **goto_kb** | Jumps into a **Knowledge Base** by name. |
| **conditional** | Routes on a variable (branches with operators). |
| **assign** | Silently sets a variable to a value. |
| **nested** | Delegates to a child canvas; its out-ports mirror the child's **exit_port**s. |
| **exit_port** | A named terminal return inside a child canvas (surfaces as a port on the parent nested node). |

@@fig:node-types@@

### Authoring rules to know

- **IDN only** today (Indonesian). Other languages are not yet enabled.
- A **conditional** can only branch on a variable that *holds a value at runtime* — a system/collected variable, or a custom variable an **assign** node set **earlier** in the flow. Branching on a never-assigned variable will fail on deploy.
- Put **assign before the conditional** that reads the variable.
- Every path should end in a terminal node (**exit**, **transfer**, **goto**, **goto_kb**, or an **exit_port**), and every **talk** node should have its **Unclassified** branch connected.`,
  },
  {
    id: 'knowledge-bases',
    title: 'Knowledge Bases & Multi-Round',
    icon: BookOpen,
    body: `## Knowledge Bases & Multi-Round

A **Knowledge Base (KB)** binds one or more **triggering intents** to an answer. When the caller says something matching an intent, the KB fires its answer — useful for FAQs and interruptions.

### Creating a KB

Ask the agent to add a knowledge base with its name, the **intents** that trigger it, and the **answer(s)**. Two rules the engine handles for you, but worth knowing:

- The triggering **intents must be declared** before the KB references them (the checker flags this as **WIZ302**).
- A KB triggered by a custom intent is an **Intent-triggered** KB (it fires on its intent), distinct from a System-triggered one.

### Multi-Round Dialogue

A KB can be **multi-round** — instead of a single answer, it delegates into a component for a short multi-turn sub-conversation. Name the target component when creating the KB and the engine wires it as a Multi-Round Dialogue.

@@fig:kb-flow@@

### Editing a KB *(in progress)*

> **Coming soon.** In-place **KB editing** — changing a KB's intents, answers, or multi-round target after creation — is being built on the engine side (the "Ethan Engine" workstream). Today you can **add** KBs through Chat; full edit support will land in a future update. Until then, to change a KB you can recreate it or use the raw-ops escape hatch.

### After import

A freshly imported KB or multi-round bot may show its nodes as *recording-pending* on the platform. Use **Batch Audio Process** in WIZ.AI to fill the audio, then deploy.`,
  },
  {
    id: 'findings',
    title: 'Findings & validation',
    icon: ShieldCheck,
    body: `## Findings & validation

The **Findings** tab runs the read-only checker over your bot and lists what it finds. The checker never changes your file.

### Severity model

- **Error** — the export is malformed and would **break import** into WIZ.AI. Fix these.
- **Warning** — the bot imports, but something is **incomplete and may break on deploy** (e.g. a flow with no way to end, or a talk node missing its Unclassified branch).

@@fig:severity@@

### Common codes

- **WIZ0xx** — schema / content (e.g. blank or truncated text).
- **WIZ1xx** — graph & flow (reachability, route validity, completeness, orphans).
- **WIZ2xx** — variables.
- **WIZ3xx** — intents (e.g. **WIZ302**: a KB's triggering intent must be declared).

### Working with findings

- **Filter** by severity to focus.
- **Ask the agent to fix** a finding straight from the list — it opens Chat with the fix request.
- The export step **warns you** if any error-level findings remain, so you don't ship a broken file by accident.`,
  },
  {
    id: 'inspect-edit',
    title: 'Inspecting & editing nodes',
    icon: MousePointerClick,
    body: `## Inspecting & editing nodes

### Selecting

Click any node in the graph, or click a finding / an inline \`#node:<id>\` link in Chat — the **Properties** tab opens and the node's owning component is focused in the graph.

### Properties tab

Properties shows the selected node's details. Two fields are **editable inline**:

- **Label** — the node's name (any node).
- **Dialogue** — the spoken prompt (nodes that have one).

Click the pencil, edit, and **Save**. Saves are applied directly and are **undoable** (use Undo in the top bar). Press **Esc** to cancel without saving.

Other attributes (branches, targets, variables, types) are read-only here — change those through **Chat**, which proposes the edit with a diff first.`,
  },
  {
    id: 'naming-export',
    title: 'Naming & export',
    icon: Download,
    body: `## Naming & export

### Naming the bot

Click the bot name in the **top bar** to rename it. This sets the export's real **speech name** — so when you import into WIZ.AI it shows your name, not "Empty Dialogue". Bots you build or scaffold are auto-named from the name you give. Renaming is undoable.

The session label in the rail mirrors the bot name, but you can also rename the *session* independently from the rail.

### Exporting

**Export** in the top bar downloads the current bot:

- **No audio** → a \`.json\` file (the dialogue export).
- **Has audio** (uploaded as a ZIP) → an import-ready **\`.zip\`** containing the \`speech*.json\` plus the WAV files.

The download is named after your bot. If there are **error-level findings**, Export asks for confirmation first. (Warnings don't block — many clean builds carry advisory warnings.)

> Built bots land their nodes as recording-pending on the platform; run **Batch Audio Process** in WIZ.AI to TTS-fill audio before deploying.`,
  },
  {
    id: 'graph',
    title: 'The flow graph',
    icon: GitBranch,
    body: `## The flow graph

The center pane renders your bot as a flow graph, laid out automatically.

- **Components** are collapsible containers — collapse the ones you're not working on to reduce clutter.
- **Color legend** — node types and edge kinds are color-coded; the legend explains the colors.
- **Search** — find a node by name and jump to it.
- **Focus** — selecting a node (from the graph, Findings, or a Chat link) focuses its owning component.
- **Pan & zoom** — drag the canvas to pan, scroll to zoom.

Orphan nodes (referenced but not defined in this export — usually links to WIZ.AI Component Library imports) are shown but are not treated as errors.`,
  },
  {
    id: 'chat-tips',
    title: 'Chat tips',
    icon: MessagesSquare,
    body: `## Chat tips

- **Slash commands** — type \`/\` at the start of the box for quick actions.
- **@-mention** — type \`@\` to reference a component or node by name.
- **Inline links** — \`#node:<id>\` in a reply is clickable and selects that node in the graph.
- **Suggestions** — chips above the input offer sensible next steps.
- **Retry / Regenerate** — re-run the last message if a turn fails, or to get a different result.
- **Cancel** — stop a turn that's still running.
- **Be specific** — name the component or node you mean ("add an exit to the *Greeting* canvas"). The agent reads the schema and facts first, so concrete asks get cleaner proposals.`,
  },
  {
    id: 'settings',
    title: 'AI settings & keys',
    icon: KeyRound,
    body: `## AI settings & keys

The Chat agent needs an LLM provider and API key. Open **Settings** from the rail footer.

- Choose a **provider** and **model**, and set your **API key** (and a base URL if you use a custom endpoint).
- The key is held for the running app and is **never shown back** to you once set.
- If no key is set, the landing screen shows a nudge with a shortcut to Settings.

You can still **upload, view, validate, and load samples** without a key — only the Chat agent (building/editing by conversation) requires one.`,
  },
];
