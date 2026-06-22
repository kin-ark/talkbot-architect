export default function DiffCard({ proposal, onApply, onReject }) {
  if (!proposal) return null;
  const d = proposal.checker_delta;
  const newErrs = d ? d.errors_after - d.errors_before : 0;
  const badge = !d ? 'new dialogue'
    : newErrs > 0 ? `⚠ +${newErrs} errors` : '✓ 0 new errors';
  return (
    <div className="border border-slate-200 rounded-lg p-3 my-2 bg-white shadow-sm" data-testid="diff-card">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs font-semibold text-slate-500">Proposed change</span>
        <span className={`text-xs font-medium ${newErrs > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>{badge}</span>
      </div>
      <pre className="text-[11px] bg-slate-50 rounded p-2 overflow-x-auto max-h-64 text-slate-700 whitespace-pre-wrap">{proposal.diff || '(no textual diff)'}</pre>
      <div className="flex gap-2 mt-2">
        <button onClick={onApply} className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700">Apply</button>
        <button onClick={onReject} className="px-3 py-1 text-sm bg-slate-100 text-slate-600 rounded hover:bg-slate-200">Reject</button>
      </div>
    </div>
  );
}
