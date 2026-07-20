import { useEffect, useRef } from 'react';
import { useFocusTrap } from '../hooks/useFocusTrap';

export default function ConfirmDialog({ title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger = false, onConfirm, onCancel }) {
  const okRef = useRef(null);
  const cancelRef = useRef(null);
  const dialogRef = useRef(null);
  useFocusTrap(dialogRef, false);   // trap Tab + restore; initial focus is Cancel (danger) or OK below
  useEffect(() => {
    (danger ? cancelRef : okRef).current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel, danger]);

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center" role="dialog" aria-modal="true" aria-label={title}>
      <div data-testid="confirm-scrim" onClick={onCancel} className="absolute inset-0 bg-black/50" />
      <div ref={dialogRef} tabIndex={-1} data-testid="confirm-dialog" className="relative bg-surface border border-border rounded-xl shadow-card w-[min(90vw,420px)] p-5">
        <h2 className="text-sm font-semibold text-text mb-1">{title}</h2>
        <p className="text-sm text-text-secondary mb-4">{message}</p>
        <div className="flex justify-end gap-2">
          <button ref={cancelRef} type="button" data-testid="confirm-cancel" onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-sm font-medium bg-surface border border-border text-text-secondary hover:bg-surface-muted">
            {cancelLabel}
          </button>
          <button ref={okRef} type="button" data-testid="confirm-ok" onClick={onConfirm}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${danger ? 'bg-error text-white hover:opacity-90' : 'bg-primary text-primary-fg hover:bg-primary-hover'}`}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
