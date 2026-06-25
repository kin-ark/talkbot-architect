import Button from './ui/Button';

export default function DiffCard({ proposal, onApply, onReject, onPreview }) {
  if (!proposal) return null;
  const d = proposal.checker_delta;
  const newErrs = d ? d.errors_after - d.errors_before : 0;
  const badge = !d ? 'new dialogue'
    : newErrs > 0 ? `⚠ +${newErrs} errors` : '✓ 0 new errors';
  const summary = proposal.change_summary;
  return (
    <div className="border border-border rounded-lg p-3 my-2 bg-surface shadow-card" data-testid="diff-card">
      <div className="flex justify-between items-center mb-2 gap-2">
        <span className="text-xs font-semibold text-text">{summary || 'Proposed change'}</span>
        <span className={`text-xs font-medium shrink-0 ${newErrs > 0 ? 'text-warning' : 'text-success'}`}>{badge}</span>
      </div>
      <details data-testid="diff-details" className="mb-2">
        <summary className="text-xs text-text-secondary cursor-pointer select-none">Show diff</summary>
        <pre className="text-[11px] bg-surface-muted rounded p-2 overflow-x-auto max-h-64 text-text whitespace-pre-wrap mt-1">{proposal.diff || '(no textual diff)'}</pre>
      </details>
      <div className="flex gap-2">
        <Button variant="primary" onClick={onApply}>Apply</Button>
        <Button variant="secondary" onClick={onReject}>Reject</Button>
        {proposal.proposed_summary && (
          <button type="button" onClick={() => onPreview?.(proposal)}
            className="ml-auto text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded px-1">
            Preview in graph
          </button>
        )}
      </div>
    </div>
  );
}
