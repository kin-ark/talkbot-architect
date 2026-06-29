import { useState, useRef } from 'react';
import { Pencil } from 'lucide-react';

function Field({ label, children }) {
  return (
    <div className="mb-4">
      <div className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm text-text">{children}</div>
    </div>
  );
}

// Inline single-line editor (Label): Enter saves, Esc cancels, blank/unchanged = no-op.
function EditableLabel({ value, onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const done = useRef(false);
  const start = () => { done.current = false; setDraft(value || ''); setEditing(true); };
  const commit = () => {
    if (done.current) return;
    done.current = true;
    setEditing(false);
    const next = draft.trim();
    if (next && next !== (value || '')) onSave(next);
  };
  const cancel = () => { done.current = true; setEditing(false); };
  if (editing) {
    return (
      <input autoFocus data-testid="label-input" value={draft}
        onChange={(e) => setDraft(e.target.value)} onBlur={commit}
        onKeyDown={(e) => { if (e.key === 'Enter') commit(); else if (e.key === 'Escape') cancel(); }}
        className="w-full bg-surface border border-border rounded px-1.5 py-0.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary" />
    );
  }
  return (
    <button type="button" data-testid="edit-label" onClick={start}
      className="group inline-flex items-center gap-1 text-sm text-text rounded px-1 -mx-1 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
      <span>{value || 'N/A'}</span>
      <Pencil size={12} className="opacity-0 group-hover:opacity-60" />
    </button>
  );
}

// Multi-line editor (Dialogue): explicit Save / Cancel.
function EditableDialogue({ value, onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const start = () => { setDraft(value || ''); setEditing(true); };
  const save = () => {
    setEditing(false);
    const next = draft.trim();
    if (next && next !== (value || '')) onSave(next);
  };
  if (editing) {
    return (
      <div>
        <textarea autoFocus data-testid="dialogue-input" rows={3} value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="w-full bg-surface border border-border rounded px-2 py-1 text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary" />
        <div className="mt-1 flex gap-2">
          <button type="button" data-testid="dialogue-save" onClick={save}
            className="text-xs rounded-md px-2 py-1 bg-primary text-primary-fg hover:bg-primary-hover">Save</button>
          <button type="button" onClick={() => setEditing(false)}
            className="text-xs rounded-md px-2 py-1 text-text-secondary hover:bg-surface-muted">Cancel</button>
        </div>
      </div>
    );
  }
  return (
    <button type="button" data-testid="edit-dialogue" onClick={start}
      className="group flex w-full items-start gap-1 text-left rounded px-1 -mx-1 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
      <span className="italic text-sm text-text">"{value}"</span>
      <Pencil size={12} className="mt-0.5 shrink-0 opacity-0 group-hover:opacity-60" />
    </button>
  );
}

export default function NodePropertiesPanel({ node, summary, onEditNode }) {
  if (!node) return <div className="p-6 text-text-tertiary text-sm" data-testid="node-properties-panel">Select a node.</div>;
  const kbTitle = (id) => (summary?.knowledge_bases || []).find((k) => k.knowledge_id === id)?.title || id;
  const edit = (fields) => onEditNode?.(node.uuid, fields);
  return (
    <div className="p-6 overflow-y-auto h-full" data-testid="node-properties-panel">
      <Field label="Label"><EditableLabel value={node.label} onSave={(v) => edit({ label: v })} /></Field>
      <Field label="Type">{node.node_type || 'N/A'}</Field>
      {node.text != null && node.text !== '' && (
        <Field label="Dialogue"><EditableDialogue value={node.text} onSave={(v) => edit({ prompt: v })} /></Field>
      )}
      {node.referenced_vars?.length > 0 && <Field label="Variables">{node.referenced_vars.join(', ')}</Field>}
      {node.allowed_kbs?.length > 0 && <Field label="Allowed KBs">{node.allowed_kbs.map(kbTitle).join(', ')}</Field>}
      {node.branches?.length > 0 && (
        <Field label="Branches / Next step">
          <ul className="space-y-1">
            {node.branches.map((b, i) => (
              <li key={i} className="text-xs bg-surface-muted border border-border rounded px-2 py-1">
                <span className="font-medium text-text">{b.label || '(unlabeled)'}</span>
                <span className="text-text-secondary"> · {b.kind}</span>
                {b.terminal && <span className="text-primary"> → {b.terminal}</span>}
                {b.target_component && <span className="text-primary"> → component</span>}
                {b.target_kb != null && <span className="text-primary"> → KB {kbTitle(b.target_kb)}</span>}
              </li>
            ))}
          </ul>
        </Field>
      )}
    </div>
  );
}
