// Bundled help content rendered by DocumentationPage. Plain markdown strings.
export const helpTopics = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    body: `## Getting Started

Talkbot Architect helps you read, build, and edit **WIZ.AI dialogue exports**.

1. **Upload** a \`speech*.json\` or a \`.zip\` export, or **Start from scratch** to describe a new bot.
2. The graph shows your flow; the right dock has **Chat**, **Findings**, **Properties**, **KB**, and **Components**.
3. Use **Chat** to ask the agent to build or change the bot. Every edit is a *proposal* — review the diff, then **Apply**.
4. **Export** downloads the current JSON.

Your work is saved as a **session**. Switch between sessions from the left rail; each keeps its own history and token usage.`,
  },
  {
    id: 'agent',
    title: 'What the agent can do',
    body: `## What the agent can do

The chat agent edits a single export. It can:

- **Validate** the export and **summarize** the flow.
- **Scaffold** a new bot or **build** from a raw manifest.
- **Add** components, nodes, intents, variables; **connect** components.
- Apply raw modifier ops or set/delete a JSON path (escape hatches).

All edit tools are **dry-run**: they return a diff + a checker delta as a proposal. Nothing changes until you **Apply**. Use **Undo**/**Redo** to step through applied changes.`,
  },
  {
    id: 'node-types',
    title: 'Node types & limits',
    body: `## Node types & limits

Eight node types are supported: **talk**, **exit**, **transfer**, **goto**, **conditional**, **assign**, **nested**, **exit_port**.

- **conditional** routes on a variable; **assign** silently sets a variable.
- **nested** delegates to a child canvas; its ports mirror the child's **exit_port**s.
- **goto** jumps to another component by name.

Authoring is **IDN only** today. A conditional can only branch on a variable that holds a value at runtime (a system variable, or a custom variable an \`assign\` populated earlier).`,
  },
  {
    id: 'chat-tips',
    title: 'Chat tips',
    body: `## Chat tips

- **Slash commands** — type \`/\` at the start of the box for quick actions.
- **@-mention** — type \`@\` to reference a component or node by name.
- **Inline links** — \`#node:<id>\` in a reply is clickable and selects that node in the graph.
- **Suggestions** — chips above the input offer next steps.
- **Retry / Regenerate** — re-run the last message if a turn fails or you want a different result.`,
  },
];
