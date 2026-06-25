import Button from './ui/Button';

export default function DiffCard({ proposal, onApply, onReject }) {
  if (!proposal) return null;
  const d = proposal.checker_delta;
  const newErrs = d ? d.errors_after - d.errors_before : 0;
  const badge = !d ? 'new dialogue'
    : newErrs > 0 ? `⚠ +${newErrs} errors` : '✓ 0 new errors';
  return (
    <div className="border border-border rounded-lg p-3 my-2 bg-surface shadow-card" data-testid="diff-card">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs font-semibold text-text-secondary">Proposed change</span>
        <span className={`text-xs font-medium ${newErrs > 0 ? 'text-warning' : 'text-success'}`}>{badge}</span>
      </div>
      <pre className="text-[11px] bg-surface-muted rounded p-2 overflow-x-auto max-h-64 text-text whitespace-pre-wrap">{proposal.diff || '(no textual diff)'}</pre>
      <div className="flex gap-2 mt-2">
        <Button variant="primary" onClick={onApply}>Apply</Button>
        <Button variant="secondary" onClick={onReject}>Reject</Button>
      </div>
    </div>
  );
}
