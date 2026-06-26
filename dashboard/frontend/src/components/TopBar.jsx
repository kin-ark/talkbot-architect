import { useState } from 'react';
import { Pencil } from 'lucide-react';
import Button from './ui/Button';

export default function TopBar({ canUndo, canRedo, onUndo, onRedo, onExport, onNew, botName, onRenameBot }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const display = botName && botName !== 'Empty Dialogue' ? botName : '';

  const start = () => { setDraft(display); setEditing(true); };
  const commit = () => {
    setEditing(false);
    const next = draft.trim();
    if (next && next !== display) onRenameBot?.(next);
  };

  return (
    <div className="h-12 border-b border-border bg-surface flex items-center justify-between px-4">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-xs font-semibold uppercase tracking-wide text-text-tertiary shrink-0">Talkbot Architect</span>
        {editing ? (
          <input autoFocus data-testid="bot-name-input" value={draft}
            onChange={(e) => setDraft(e.target.value)} onBlur={commit}
            onKeyDown={(e) => { if (e.key === 'Enter') commit(); else if (e.key === 'Escape') { setDraft(display); setEditing(false); } }}
            className="min-w-0 bg-surface border border-border rounded px-1.5 py-0.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary" />
        ) : (
          <button type="button" data-testid="bot-name" onClick={start}
            className="group flex items-center gap-1 min-w-0 rounded px-1.5 py-0.5 text-sm font-semibold text-text hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
            <span className="truncate">{display || 'Untitled bot'}</span>
            <Pencil size={12} className="shrink-0 opacity-0 group-hover:opacity-60" />
          </button>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Button variant="secondary" onClick={onNew}>New / Upload</Button>
        <Button variant="secondary" onClick={onUndo} disabled={!canUndo}>Undo</Button>
        <Button variant="secondary" onClick={onRedo} disabled={!canRedo}>Redo</Button>
        <Button variant="secondary" onClick={onExport}>Export</Button>
      </div>
    </div>
  );
}
