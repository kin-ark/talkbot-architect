import { useEffect } from 'react';
import { X } from 'lucide-react';

export default function PageOverlay({ title, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div data-testid="page-overlay" className="fixed inset-0 z-50 flex items-center justify-center">
      <div data-testid="page-scrim" onClick={onClose} className="absolute inset-0 bg-black/50" />
      <div role="dialog" aria-label={title}
        className="relative bg-surface border border-border rounded-xl shadow-card w-[min(90vw,640px)] max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-divider">
          <h2 className="text-sm font-semibold text-text">{title}</h2>
          <button type="button" data-testid="page-close" aria-label="Close" onClick={onClose}
            className="p-1 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text">
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}
