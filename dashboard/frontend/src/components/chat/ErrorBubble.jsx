import { useState } from 'react';
import { AlertTriangle, ChevronRight } from 'lucide-react';
import { classifyError } from './errorInfo';
import RecoveryBar from './RecoveryBar';
import { tokensFor } from './recovery';

export default function ErrorBubble({ text, kind, recovery, onRetry, onContinue, onFix, onEdit, onDiscard }) {
  const [open, setOpen] = useState(false);
  const { title, hint, detail } = classifyError(text);
  // Only offer raw detail when it adds something beyond the friendly title/hint.
  const showDetail = detail && detail.toLowerCase() !== title.toLowerCase();
  const tokens = tokensFor({ kind, recovery });

  return (
    <div className="text-left" data-testid="error-bubble">
      <div className="text-xs text-text-tertiary mb-0.5">Error</div>
      <div className="inline-block max-w-[80%] p-3 rounded-2xl text-sm bg-error-bg border border-error text-error">
        <div className="flex items-start gap-2">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          <div className="min-w-0">
            <div className="font-medium">{title}</div>
            {hint && <div className="mt-0.5 text-text-secondary">{hint}</div>}
            {showDetail && (
              <div className="mt-1.5">
                <button type="button" data-testid="error-detail-toggle" onClick={() => setOpen((v) => !v)}
                  className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
                  <ChevronRight size={12} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
                  Details
                </button>
                {open && (
                  <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] text-text-tertiary bg-surface-muted rounded p-2 border border-border">
                    {detail}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      <RecoveryBar tokens={tokens} onRetry={onRetry} onContinue={onContinue}
        onFix={onFix} onEdit={onEdit} onDiscard={onDiscard} />
    </div>
  );
}
