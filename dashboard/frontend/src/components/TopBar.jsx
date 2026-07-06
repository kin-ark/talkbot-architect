import { useState } from 'react';
import { Pencil, Undo2, Redo2, Puzzle } from 'lucide-react';
import Button from './ui/Button';

export default function TopBar({ hasDoc, canUndo, canRedo, onUndo, onRedo, onExport, botName, onRenameBot, isComponent }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const display = botName && botName !== 'Empty Dialogue' ? botName : '';

  const start = () => { if (!hasDoc) return; setDraft(display); setEditing(true); };
  const commit = () => {
    setEditing(false);
    const next = draft.trim();
    if (next && next !== display) onRenameBot?.(next);
  };

  return (
    <div className="h-12 border-b border-border bg-surface flex items-center justify-between px-4">
      <div className="flex items-center gap-2 min-w-0">
        <img src="/favicon.svg" alt="" className="w-5 h-5 shrink-0" />
        {!hasDoc ? (
          <span data-testid="bot-name" className="text-sm font-semibold text-text-tertiary truncate">Talkbot Architect</span>
        ) : editing ? (
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
        {isComponent && (
          <span data-testid="component-badge"
            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-surface-secondary text-text-secondary border border-border"
            title="Component export — exports as a component envelope">
            <Puzzle size={12} /> Component
          </span>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button type="button" aria-label="Undo" title="Undo" onClick={onUndo} disabled={!hasDoc || !canUndo}
          className="p-2 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-text-secondary">
          <Undo2 size={16} />
        </button>
        <button type="button" aria-label="Redo" title="Redo" onClick={onRedo} disabled={!hasDoc || !canRedo}
          className="p-2 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-text-secondary">
          <Redo2 size={16} />
        </button>
        <Button variant="secondary" onClick={onExport} disabled={!hasDoc} className="ml-1">Export</Button>
      </div>
    </div>
  );
}
