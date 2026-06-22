
function Field({ label, children }) {
  return (
    <div className="mb-4">
      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm text-slate-700">{children}</div>
    </div>
  );
}

export default function NodePropertiesPanel({ node, summary }) {
  if (!node) return <div className="p-6 text-slate-400 text-sm" data-testid="node-properties-panel">Select a node.</div>;
  const kbTitle = (id) => (summary?.knowledge_bases || []).find((k) => k.knowledge_id === id)?.title || id;
  return (
    <div className="p-6 overflow-y-auto h-full" data-testid="node-properties-panel">
      <Field label="Label">{node.label || 'N/A'}</Field>
      <Field label="Type">{node.node_type || 'N/A'}</Field>
      {node.text && <Field label="Dialogue"><span className="italic">"{node.text}"</span></Field>}
      {node.referenced_vars?.length > 0 && <Field label="Variables">{node.referenced_vars.join(', ')}</Field>}
      {node.allowed_kbs?.length > 0 && <Field label="Allowed KBs">{node.allowed_kbs.map(kbTitle).join(', ')}</Field>}
      {node.branches?.length > 0 && (
        <Field label="Branches / Next step">
          <ul className="space-y-1">
            {node.branches.map((b, i) => (
              <li key={i} className="text-xs bg-slate-50 border border-slate-200 rounded px-2 py-1">
                <span className="font-medium">{b.label || '(unlabeled)'}</span>
                <span className="text-slate-400"> · {b.kind}</span>
                {b.terminal && <span className="text-sky-600"> → {b.terminal}</span>}
                {b.target_component && <span className="text-sky-600"> → component</span>}
                {b.target_kb != null && <span className="text-sky-600"> → KB {kbTitle(b.target_kb)}</span>}
              </li>
            ))}
          </ul>
        </Field>
      )}
    </div>
  );
}
