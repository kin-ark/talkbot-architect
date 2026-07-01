import { useState } from 'react';
import FilterChips from './ui/FilterChips';

const FILTERS = [['all', 'All'], ['intent', 'Intent'], ['system', 'System'], ['multi-round', 'Multi-round'], ['user', 'User-created']];

export default function KBPlane({ knowledgeBases = [], onSelect }) {
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const q = query.trim().toLowerCase();
  const shown = knowledgeBases.filter((kb) => {
    const typeOk = filter === 'all' ? true
      : filter === 'intent' ? kb.trigger_type === 'intent'
      : filter === 'system' ? kb.trigger_type === 'system'
      : filter === 'multi-round' ? !!kb.multi_round
      : filter === 'user' ? !!kb.is_user_created
      : true;
    return typeOk && (!q || (kb.title || '').toLowerCase().includes(q));
  });
  return (
    <div className="p-4 overflow-y-auto h-full" data-testid="kb-plane">
      <FilterChips options={FILTERS} value={filter} onChange={setFilter} />
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search knowledge bases…"
        data-testid="kb-search"
        className="mt-2 mb-3 w-full border border-border rounded-md px-2 py-1 text-xs bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary" />
      {shown.length === 0 ? (
        <p className="text-sm text-text-tertiary">{knowledgeBases.length === 0 ? 'No knowledge bases yet.' : 'No knowledge bases match.'}</p>
      ) : (
        <ul className="space-y-2">
          {shown.map((kb) => (
            <li key={kb.knowledge_id} data-testid="kb-row" onClick={() => onSelect?.(kb)}
              className="p-3 rounded border border-border cursor-pointer hover:bg-surface-muted">
              <div className="flex justify-between items-center gap-2">
                <span className="text-sm font-medium text-text truncate">{kb.title}</span>
                <span className="flex items-center gap-1">
                  <span className="text-[10px] rounded px-1.5 py-0.5 text-text-tertiary bg-surface-muted">{kb.trigger_type === 'system' ? 'System' : 'Intent'}</span>
                  {kb.multi_round && <span className="text-[10px] bg-surface-muted text-primary rounded px-1.5 py-0.5">multi-round ▸</span>}
                </span>
              </div>
              <div className="text-[11px] text-text-tertiary">id {kb.knowledge_id} · {(kb.intents?.length ?? 0)} intents</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
