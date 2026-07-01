import { useState } from 'react';
import FilterChips from './ui/FilterChips';

export default function ComponentsRail({ summary, selectedComponentId, onSelectComponent }) {
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
            <button type="button" key={c.uuid} onClick={() => onSelectComponent(c.uuid)}
              className={`w-full flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                active ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted'}`}>
              <span className="truncate">{c.name}</span>
              <span className="ml-auto text-xs text-text-tertiary">{count}</span>
            </button>
          );
        })}
        {components.length === 0 && <p className="px-2 py-3 text-xs text-text-tertiary">No components yet.</p>}
        {components.length > 0 && shown.length === 0 && <p className="px-2 py-3 text-xs text-text-tertiary">No components match.</p>}
      </div>
    </div>
  );
}
