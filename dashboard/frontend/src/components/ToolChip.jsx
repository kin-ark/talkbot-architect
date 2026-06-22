export default function ToolChip({ name, args }) {
  const label = { validate: '🔍 Validating', summarize: '🗺️ Summarizing', read_node: '📖 Reading node',
    apply_mods: '✏️ Proposing edits', set_path: '✏️ Editing', delete_path: '🗑️ Deleting',
    build: '🏗️ Scaffolding', get_facts: '📚 Looking up facts' }[name] || name;
  return <span className="inline-flex items-center text-xs bg-slate-100 text-slate-600 rounded px-2 py-0.5 mr-1 mb-1" title={JSON.stringify(args)}>{label}</span>;
}
