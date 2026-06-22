
function Group({ title, items, color, onSelect }) {
  return (
    <div className="mb-4">
      <h3 className={`text-xs font-bold uppercase tracking-wider mb-2 ${color}`}>{title} ({items.length})</h3>
      <ul className="space-y-1">
        {items.map((f, i) => (
          <li key={i} onClick={() => f.id && onSelect?.({ uuid: f.id })}
            className="text-xs p-2 rounded border border-slate-200 hover:bg-slate-50 cursor-pointer">
            <span className="font-mono font-semibold">{f.code}</span> — {f.message}
            {f.entity && <span className="text-slate-400"> [{f.entity}{f.id ? ` ${f.id}` : ''}]</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function FindingList({ findings = [], onSelect }) {
  const errors = findings.filter((f) => f.severity === 'error');
  const warnings = findings.filter((f) => f.severity === 'warning');
  return (
    <div className="p-4 overflow-y-auto h-full" data-testid="finding-list">
      {findings.length === 0 && <p className="text-sm text-emerald-600">No findings. ✓</p>}
      {errors.length > 0 && <Group title="Errors" items={errors} color="text-red-600" onSelect={onSelect} />}
      {warnings.length > 0 && <Group title="Warnings" items={warnings} color="text-amber-600" onSelect={onSelect} />}
    </div>
  );
}
