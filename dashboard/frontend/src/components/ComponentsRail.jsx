import { useState } from 'react';
import { Puzzle } from 'lucide-react';
import FilterChips from './ui/FilterChips';
import IconButton from './ui/IconButton';

export default function ComponentsRail({ summary, selectedComponentId, onSelectComponent, onExportComponent }) {
  const components = summary?.components || [];
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();

  const types = Array.from(new Set(
    components.flatMap((c) => Object.values(c.nodes || {}).map((n) => n.node_type)).filter(Boolean)
  )).sort();
  const options = [['all', 'All'], ...types.map((t) => [t, t])];

  const matchCount = (c) => Object.values(c.nodes || {}).filter((n) => n.node_type === filter).length;
  const shown = components.filter((c) => {
    const typeOk = filter === 'all' ? true : matchCount(c) > 0;
    return typeOk && (!q || (c.name || '').toLowerCase().includes(q));
  });

  return (
    <div className="w-56 shrink-0 h-full border-r border-border bg-surface flex flex-col" data-testid="components-rail">
      <div className="px-3 py-2 border-b border-divider space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-text-tertiary">Components</div>
        <FilterChips options={options} value={filter} onChange={setFilter} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search…"
          data-testid="component-search"
          className="w-full border border-border rounded-md px-2 py-1 text-xs bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {shown.map((c) => {
          const total = Object.keys(c.nodes || {}).length;
          const active = c.uuid === selectedComponentId;
          const count = filter === 'all' ? `${total}` : `${matchCount(c)}/${total}`;
          return (
            <div key={c.uuid} className="flex items-center gap-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              style={{ outline: active ? '2px solid var(--color-primary)' : 'none', borderRadius: '0.375rem' }}>
              <button type="button" onClick={() => onSelectComponent(c.uuid)}
                className={`flex-1 min-w-0 text-left px-2.5 py-1.5 text-sm rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                  active ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted'}`}>
                <span className="truncate">{c.name}</span>
              </button>
              <span className="px-1 text-xs text-text-tertiary">{count}</span>
              {onExportComponent && (
                <IconButton label="Export as component" data-testid={`export-component-${c.uuid}`}
                  onClick={(e) => { e.stopPropagation(); onExportComponent(c.uuid); }} className="h-6 w-6 shrink-0 mr-1">
                  <Puzzle size={13} />
                </IconButton>
              )}
            </div>
          );
        })}
        {components.length === 0 && <p className="px-2 py-3 text-xs text-text-tertiary">No components yet.</p>}
        {components.length > 0 && shown.length === 0 && <p className="px-2 py-3 text-xs text-text-tertiary">No components match.</p>}
      </div>
    </div>
  );
}
