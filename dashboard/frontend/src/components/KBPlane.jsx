
export default function KBPlane({ knowledgeBases = [], onDrillIn }) {
  return (
    <div className="p-4 overflow-y-auto h-full" data-testid="kb-plane">
      <ul className="space-y-2">
        {knowledgeBases.map((kb) => (
          <li key={kb.knowledge_id} onClick={() => kb.multi_round && onDrillIn?.(kb)}
            className={`p-3 rounded border border-slate-200 ${kb.multi_round ? 'cursor-pointer hover:bg-slate-50' : ''}`}>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-slate-700">{kb.title}</span>
              {kb.multi_round && <span className="text-[10px] bg-indigo-100 text-indigo-600 rounded px-1.5 py-0.5">multi-round ▸</span>}
            </div>
            <div className="text-[11px] text-slate-400">id {kb.knowledge_id} · {(kb.intents?.length ?? 0)} intents</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
