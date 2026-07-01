import { useState } from 'react';
import FilterChips from './ui/FilterChips';

const FILTERS = [['all', 'All'], ['user', 'User'], ['system', 'System'], ['needs-nlu', 'Needs NLU']];

function TypeBadge({ type }) {
  const cls = type === 'user' ? 'text-primary bg-surface-muted' : 'text-text-tertiary bg-surface-muted';
  return <span className={`text-[10px] rounded px-1.5 py-0.5 ${cls}`}>{type === 'user' ? 'User' : 'System'}</span>;
}

export default function IntentsPanel({ intents = [] }) {
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const shown = intents.filter((i) => {
    const typeOk = filter === 'all' ? true
      : filter === 'needs-nlu' ? i.needs_nlu
      : i.type === filter;
    return typeOk && (!q || (i.name || '').toLowerCase().includes(q));
  });
  return (
    <div className="p-4 overflow-y-auto h-full" data-testid="intents-panel">
      <FilterChips options={FILTERS} value={filter} onChange={setFilter} />
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search intents…"
        data-testid="intent-search"
        className="mt-2 mb-3 w-full border border-border rounded-md px-2 py-1 text-xs bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary" />
      {intents.length === 0 ? (
        <p className="text-sm text-text-tertiary">No intents yet.</p>
      ) : shown.length === 0 ? (
        <p className="text-sm text-text-tertiary">No intents match.</p>
      ) : (
        <>
          <div className="text-xs text-text-tertiary mb-2">{shown.length} intent{shown.length === 1 ? '' : 's'}</div>
          <ul className="space-y-1">
            {shown.map((i) => (
              <li key={i.id ?? i.name} data-testid="intent-row" className="p-2 rounded border border-border">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text truncate">{i.name}</span>
                  <span className="ml-auto"><TypeBadge type={i.type} /></span>
                </div>
                <div className="text-[11px] text-text-tertiary">
                  {i.keyword_count} keywords · {i.response_count} responses
                  {i.needs_nlu && <span className="ml-2 text-warning">no NLU signal</span>}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
