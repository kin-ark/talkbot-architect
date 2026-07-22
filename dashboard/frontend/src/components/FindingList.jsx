import { useState } from 'react';

function Group({ title, items, color, onSelect, onAskFix }) {
  return (
    <div className="mb-4">
      <h3 className={`text-xs font-bold uppercase tracking-wider mb-2 ${color}`}>{title} ({items.length})</h3>
      <ul className="space-y-1">
        {items.map((f, i) => (
          <li key={i} className="text-xs p-2 rounded border border-border hover:bg-surface-muted text-text">
            <div
              {...(f.id ? {
                role: 'button', tabIndex: 0,
                onClick: () => onSelect?.({ uuid: f.id }),
                onKeyDown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.({ uuid: f.id }); } },
              } : {})}
              className={f.id ? 'cursor-pointer' : ''}>
              <span className="font-mono font-semibold">{f.code}</span> — {f.message}
              {f.entity && <span className="text-text-tertiary"> [{f.entity}{f.id ? ` ${f.id}` : ''}]</span>}
            </div>
            <button type="button" onClick={() => onAskFix?.(f)}
              className="mt-1 text-[11px] text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
              Fix with chat
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

const FILTERS = [['all', 'All'], ['error', 'Errors'], ['warning', 'Warnings']];

export default function FindingList({ findings = [], onSelect, onAskFix }) {
  const [filter, setFilter] = useState('all');
  const errors = findings.filter((f) => f.severity === 'error');
  const warnings = findings.filter((f) => f.severity === 'warning');
  const showErrors = filter === 'all' || filter === 'error';
  const showWarnings = filter === 'all' || filter === 'warning';
  return (
    <div className="p-4 overflow-y-auto h-full" data-testid="finding-list">
      <div className="flex gap-1 mb-3">
        {FILTERS.map(([id, label]) => (
          <button key={id} type="button" onClick={() => setFilter(id)}
            className={`text-xs rounded-md px-2 py-0.5 border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${filter === id ? 'bg-primary text-primary-fg' : 'text-text-secondary hover:bg-surface-muted'}`}>
            {label}
          </button>
        ))}
      </div>
      {findings.length === 0 && <p className="text-sm text-success">No findings.</p>}
      {showErrors && errors.length > 0 && <Group title="Errors" items={errors} color="text-error" onSelect={onSelect} onAskFix={onAskFix} />}
      {showWarnings && warnings.length > 0 && <Group title="Warnings" items={warnings} color="text-warning" onSelect={onSelect} onAskFix={onAskFix} />}
    </div>
  );
}
