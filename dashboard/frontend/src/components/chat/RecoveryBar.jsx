import { RotateCcw, ArrowRight, Wrench, Pencil, X } from 'lucide-react';

const SPEC = {
  retry:    { label: 'Retry', Icon: RotateCcw, prop: 'onRetry' },
  continue: { label: 'Continue', Icon: ArrowRight, prop: 'onContinue' },
  fix:      { label: 'Fix errors', Icon: Wrench, prop: 'onFix' },
  edit:     { label: 'Edit & resend', Icon: Pencil, prop: 'onEdit' },
  discard:  { label: 'Discard', Icon: X, prop: 'onDiscard' },
};

export default function RecoveryBar({ tokens = [], ...handlers }) {
  const items = tokens.map((t) => SPEC[t]).filter(Boolean);
  if (items.length === 0) return null;
  return (
    <div className="mt-1 flex flex-wrap gap-2" data-testid="recovery-bar">
      {items.map(({ label, Icon, prop }) => (
        <button key={prop} type="button" onClick={handlers[prop]}
          className="inline-flex items-center gap-1 text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
          <Icon size={12} /> {label}
        </button>
      ))}
    </div>
  );
}
