import { useState } from 'react';
import { useConfirm } from '../confirm/ConfirmProvider';
import { Plus, Pencil, Trash2, PanelLeftClose, PanelLeftOpen, MessageSquare, BarChart3, BookOpen, Settings, Sun, Moon } from 'lucide-react';

function fmtUsage(u) {
  if (!u) return null;
  const inp = u.input_tokens || 0;
  const out = u.output_tokens || 0;
  return `${inp} in · ${out} out · ${u.turns || 0} turns`;
}

function SessionRow({ s, active, onSwitch, onRename, onDelete, collapsed }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(s.name);
  const confirm = useConfirm();

  const commit = () => {
    setEditing(false);
    const next = name.trim();
    if (next && next !== s.name) onRename(s.id, next);
    else setName(s.name);
  };

  const base = 'group w-full flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-left cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary';
  const tone = active ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted';

  if (collapsed) {
    return (
      <button type="button" data-testid="session-row" title={s.name}
        onClick={() => onSwitch(s.id)}
        className={`flex items-center justify-center w-9 h-9 mx-auto rounded-md ${tone}`}>
        <span className="text-xs">{(s.name || '?').slice(0, 1).toUpperCase()}</span>
      </button>
    );
  }

  return (
    <div data-testid="session-row" role="button" tabIndex={0}
      onClick={() => { if (!editing) onSwitch(s.id); }}
      onKeyDown={(e) => { if (!editing && (e.key === 'Enter' || e.key === ' ')) onSwitch(s.id); }}
      className={`${base} ${tone}`}>
      <MessageSquare size={14} className="shrink-0 opacity-70" />
      {editing ? (
        <input autoFocus value={name} onChange={(e) => setName(e.target.value)}
          onClick={(e) => e.stopPropagation()} onBlur={commit}
          onKeyDown={(e) => { e.stopPropagation();
            if (e.key === 'Enter') commit();
            else if (e.key === 'Escape') { setEditing(false); setName(s.name); } }}
          className="flex-1 min-w-0 bg-surface border border-border rounded px-1 py-0.5 text-sm text-text" />
      ) : (
        <span className="truncate flex-1">{s.name}</span>
      )}
      {!editing && (
        <span className="ml-auto hidden group-hover:flex items-center gap-1">
          <button type="button" aria-label="Rename session"
            onClick={(e) => { e.stopPropagation(); setName(s.name); setEditing(true); }}
            className="p-0.5 rounded hover:bg-surface text-text-tertiary hover:text-text">
            <Pencil size={13} />
          </button>
          <button type="button" aria-label="Delete session"
            onClick={async (e) => {
              e.stopPropagation();
              const ok = await confirm({
                title: 'Delete session?',
                message: `Delete "${s.name}"? This cannot be undone.`,
                confirmLabel: 'Delete', danger: true,
              });
              if (ok) onDelete(s.id);
            }}
            className="p-0.5 rounded hover:bg-surface text-text-tertiary hover:text-error">
            <Trash2 size={13} />
          </button>
        </span>
      )}
    </div>
  );
}

export default function SessionRail({ sessions = [], activeSessionId, onNew, onSwitch,
  onRename, onDelete, usage, collapsed, onToggleCollapse, onOpenPage, theme, onToggleTheme }) {
  const widthCls = collapsed ? 'w-12' : 'w-60';
  return (
    <div data-testid="session-rail"
      className={`${widthCls} shrink-0 h-full border-r border-border bg-surface flex flex-col`}>
      <div className="flex items-center gap-1 px-2 py-2 border-b border-divider">
        {!collapsed && <span className="text-sm font-semibold text-text px-1">Sessions</span>}
        <div className="ml-auto flex items-center gap-1">
          <button type="button" data-testid="rail-new" aria-label="New session" title="New session"
            onClick={onNew}
            className="p-1.5 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text">
            <Plus size={16} />
          </button>
          <button type="button" data-testid="rail-collapse"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={onToggleCollapse}
            className={`p-1.5 rounded-md hover:bg-surface-muted ${collapsed
              ? 'text-primary bg-surface-muted ring-1 ring-border hover:text-primary'
              : 'text-text-secondary hover:text-text'}`}>
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>
      </div>

      <div className={`flex-1 overflow-y-auto p-2 ${collapsed ? 'space-y-1' : 'space-y-0.5'}`}>
        {sessions.map((s) => (
          <SessionRow key={s.id} s={s} active={s.id === activeSessionId}
            onSwitch={onSwitch} onRename={onRename} onDelete={onDelete} collapsed={collapsed} />
        ))}
        {sessions.length === 0 && !collapsed && (
          <p className="px-2 py-3 text-xs text-text-tertiary">No sessions yet.</p>
        )}
      </div>

      <div className={`border-t border-divider p-2 flex ${collapsed ? 'flex-col items-center gap-1' : 'items-center gap-1'}`}>
        <button type="button" data-testid="rail-stats" aria-label="Statistics" title="Statistics"
          onClick={() => onOpenPage?.('stats')}
          className="p-1.5 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text">
          <BarChart3 size={16} />
        </button>
        <button type="button" data-testid="rail-docs" aria-label="Documentation" title="Documentation"
          onClick={() => onOpenPage?.('docs')}
          className="p-1.5 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text">
          <BookOpen size={16} />
        </button>
        <button type="button" data-testid="rail-settings" aria-label="Settings" title="Settings"
          onClick={() => onOpenPage?.('settings')}
          className="p-1.5 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text">
          <Settings size={16} />
        </button>
        <button type="button" data-testid="rail-theme"
          aria-label="Toggle theme" title="Toggle light/dark"
          onClick={() => onToggleTheme?.()}
          className={`p-1.5 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text ${collapsed ? '' : 'ml-auto'}`}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>

      {!collapsed && (
        <div data-testid="rail-usage" className="border-t border-divider px-3 py-2 text-xs text-text-tertiary space-y-0.5">
          {usage?.model && <div className="truncate" title={usage.model}>Model: {usage.model}</div>}
          <div>{fmtUsage(usage) || 'No usage yet'}</div>
        </div>
      )}
    </div>
  );
}
