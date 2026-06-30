import { useSyncExternalStore } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import { subscribe, getSnapshot, dismiss } from '../toast/toastStore';
import IconButton from './ui/IconButton';

const ICON = { success: CheckCircle2, error: AlertCircle, info: Info };
const TONE = { success: 'text-success', error: 'text-error', info: 'text-primary' };

export default function ToastViewport() {
  const toasts = useSyncExternalStore(subscribe, getSnapshot);
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => {
        const Icon = ICON[t.kind] || Info;
        return (
          <div key={t.id} data-testid="toast" data-kind={t.kind}
            role={t.kind === 'error' ? 'alert' : 'status'}
            className="pointer-events-auto flex items-start gap-2 max-w-sm rounded-lg border border-border bg-surface shadow-card px-3 py-2 text-sm">
            <Icon size={16} className={`mt-0.5 shrink-0 ${TONE[t.kind] || 'text-primary'}`} />
            <span className="flex-1 text-text">{t.message}</span>
            <IconButton label="Dismiss" data-testid="toast-dismiss" onClick={() => dismiss(t.id)} className="h-6 w-6 -mr-1 -mt-0.5">
              <X size={14} />
            </IconButton>
          </div>
        );
      })}
    </div>
  );
}
