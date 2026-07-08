import { useRef, useState, useLayoutEffect } from 'react';
import { Paperclip, X } from 'lucide-react';
import { attachFile, clearAttachment } from '../../api';

const MAX_H = 144; // ~6 lines

export default function ChatInput({ value, onChange, onSubmit, sending, onCancel,
  slashMatches, mentionMatches, onPickSlash, onPickMention }) {
  const taRef = useRef(null);
  const fileInputRef = useRef(null);
  const [dismissed, setDismissed] = useState(false);
  const [attachment, setAttachment] = useState(null);
  const [attaching, setAttaching] = useState(false);

  const slashOpen = !dismissed && slashMatches.length > 0;
  const mentionOpen = !dismissed && mentionMatches.length > 0;

  // Auto-grow to fit content up to MAX_H.
  const resize = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, MAX_H) + 'px';
  };
  useLayoutEffect(resize, [value]);

  const trySubmit = () => {
    if (!value.trim() || sending) return;
    onSubmit();
    setAttachment(null);
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAttaching(true);
    try {
      const result = await attachFile(file);
      setAttachment(result);
    } catch (err) {
      console.error('attach failed:', err);
    } finally {
      setAttaching(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const onKeyDown = (e) => {
    if (e.nativeEvent?.isComposing) return;
    if (e.key === 'Escape') { if (slashOpen || mentionOpen) { e.preventDefault(); setDismissed(true); } return; }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (slashOpen) { onPickSlash(slashMatches[0]); return; }
      if (mentionOpen) { onPickMention(mentionMatches[0]); return; }
      trySubmit();
    }
  };

  const onForm = (e) => { e.preventDefault(); trySubmit(); };

  return (
    <form onSubmit={onForm} data-testid="chat-form" className="p-4 border-t border-border bg-surface">
      <div className="relative flex gap-2 items-end">
        {slashOpen && (
          <div data-testid="slash-menu"
            className="absolute bottom-full mb-1 left-0 w-72 rounded-lg border border-border bg-surface shadow-card overflow-hidden z-30">
            {slashMatches.map((c) => (
              <button key={c.cmd} type="button" onClick={() => onPickSlash(c)}
                className="block w-full text-left px-3 py-1.5 text-sm text-text hover:bg-surface-muted">
                <span className="font-mono text-primary">{c.cmd}</span>
                <span className="text-text-tertiary"> — {c.text.trim() || '…'}</span>
              </button>
            ))}
          </div>
        )}
        {mentionOpen && (
          <div data-testid="mention-menu"
            className="absolute bottom-full mb-1 left-0 w-72 max-h-60 overflow-y-auto rounded-lg border border-border bg-surface shadow-card z-30">
            {mentionMatches.map((e2) => (
              <button key={`${e2.kind}-${e2.uuid}`} type="button" onClick={() => onPickMention(e2)}
                className="block w-full text-left px-3 py-1.5 text-sm text-text hover:bg-surface-muted">
                <span className="text-text-tertiary text-xs uppercase mr-2">{e2.kind === 'component' ? 'comp' : 'node'}</span>
                {e2.label}
              </button>
            ))}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <textarea ref={taRef} rows={1} value={value}
            onChange={(e) => { setDismissed(false); onChange(e.target.value); }}
            onInput={resize}
            onKeyDown={onKeyDown}
            aria-label="Chat message"
            placeholder="Ask about or edit the dialogue…"
            className="w-full resize-none border border-border rounded-xl px-3 py-2 text-sm text-text bg-surface focus:outline-none focus:ring-2 focus:ring-primary"
            style={{ maxHeight: MAX_H }} />
          {attachment && (
            <div className="text-[11px] text-text-tertiary mt-0.5 px-1 flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 bg-surface-muted px-2 py-1 rounded">
                {attachment.name}
                <button type="button" onClick={() => {
                  clearAttachment().catch(err => console.error('clear failed:', err));
                  setAttachment(null);
                }} disabled={sending} className="p-0 text-text-tertiary hover:text-text">
                  <X size={14} />
                </button>
              </span>
            </div>
          )}
          {!attachment && (
            <div className="text-[11px] text-text-tertiary mt-0.5 px-1">Enter to send · Shift+Enter for newline</div>
          )}
        </div>
        <input ref={fileInputRef} type="file" onChange={handleFileSelect} className="hidden" data-testid="file-input" />
        <button type="button" onClick={() => fileInputRef.current?.click()} disabled={sending || attaching}
          className="p-2 text-text-tertiary hover:text-text hover:bg-surface-muted rounded-lg transition-colors"
          title="Attach file" data-testid="attach-button">
          <Paperclip size={20} />
        </button>
        {sending
          ? <button type="button" onClick={onCancel} className="px-4 h-[38px] bg-error text-primary-fg rounded-xl hover:opacity-90">Stop</button>
          : <button type="submit" className="px-4 h-[38px] bg-primary text-primary-fg rounded-xl hover:bg-primary-hover">Send</button>}
      </div>
    </form>
  );
}
