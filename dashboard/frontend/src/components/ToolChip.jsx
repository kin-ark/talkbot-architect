const LABELS = {
  validate: 'Validating', summarize: 'Summarizing', read_node: 'Reading node',
  get_facts: 'Looking up facts', get_schema: 'Reading schema',
  scaffold_bot: 'Scaffolding bot', build: 'Building',
  add_component: 'Adding component', add_node: 'Adding node',
  connect_components: 'Connecting', add_intent: 'Adding intent',
  add_variable: 'Adding variable', apply_mods: 'Proposing edits',
  set_path: 'Editing', delete_path: 'Deleting',
};

export default function ToolChip({ name, args, status, summary }) {
  const label = LABELS[name] || name;
  return (
    <span className="inline-flex items-center gap-1 text-xs bg-surface-muted text-primary rounded px-2 py-0.5 mr-1 mb-1"
      title={JSON.stringify(args)}>
      {label}
      {status === 'running' && <span className="animate-pulse">·</span>}
      {status === 'done' && summary && <span className="text-text-tertiary">— {summary}</span>}
    </span>
  );
}
