import { useState } from 'react';
import { X } from 'lucide-react';

export default function WelcomeCard() {
  const [hidden, setHidden] = useState(() => {
    try { return localStorage.getItem('tb-welcome-dismissed') === '1'; } catch { return false; }
  });
  if (hidden) return null;
  const dismiss = () => {
    try { localStorage.setItem('tb-welcome-dismissed', '1'); } catch { /* ignore */ }
    setHidden(true);
  };
  return (
    <div data-testid="welcome-card" className="relative mb-4 rounded-xl border border-border bg-surface-muted p-4 text-sm text-text">
      <button type="button" data-testid="welcome-dismiss" aria-label="Dismiss" onClick={dismiss}
        className="absolute top-2 right-2 p-1 rounded-md text-text-secondary hover:bg-surface hover:text-text">
        <X size={14} />
      </button>
      <p className="font-semibold mb-1">Welcome to Talkbot Architect</p>
      <p className="text-text-secondary">Upload a WIZ dialogue export, try a sample below, or describe a bot in chat — the assistant builds and validates it for you.</p>
    </div>
  );
}
