import { useRef, useState, useLayoutEffect } from 'react';
import { Paperclip, X } from 'lucide-react';
import { attachFile, clearAttachment, clearImage } from '../../api';

const MAX_H = 144; // ~6 lines

export default function ChatInput({ value, onChange, onSubmit, sending, onCancel,
  slashMatches, mentionMatches, onPickSlash, onPickMention, canSendImages = true }) {
  const taRef = useRef(null);
  const fileInputRef = useRef(null);
  const [dismissed, setDismissed] = useState(false);
  const [attachment, setAttachment] = useState(null);
  const [attaching, setAttaching] = useState(false);
  const [images, setImages] = useState([]);

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
    setImages([]);
  };

  const uploadImage = async (file) => {
    try {
      const r = await attachFile(file);
      if (r.kind === 'image') {
        setImages((xs) => [...xs, { name: r.name, url: URL.createObjectURL(file) }]);
      }
    } catch (err) {
      console.error('attach failed:', err);
    }
  };

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (!files) return;
    setAttaching(true);
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const result = await attachFile(file);
        if (result.kind === 'image') {
          setImages((xs) => [...xs, { name: result.name, url: URL.createObjectURL(file) }]);
        } else {
          setAttachment(result);
        }
      }
    } catch (err) {
      console.error('attach failed:', err);
    } finally {
      setAttaching(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const onPaste = async (e) => {
    if (!canSendImages) return;
    const items = Array.from(e.clipboardData?.items || []);
    const imgs = items.filter((it) => it.kind === 'file' && it.type.startsWith('image/'));
    if (!imgs.length) return;
    e.preventDefault();
    setAttaching(true);
    try {
      for (const it of imgs) {
        const f = it.getAsFile();
        if (f) await uploadImage(f);
      }
    } finally {
      setAttaching(false);
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
            className="absolute bottom-full mb-1 left-0 w-80 max-h-72 overflow-y-auto rounded-lg border border-border bg-surface shadow-card z-30">
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
            className="absolute bottom-full mb-1 left-0 w-80 max-h-72 overflow-y-auto rounded-lg border border-border bg-surface shadow-card z-30">
            {mentionMatches.map((e2) => (
              <button key={`${e2.kind}-${e2.uuid}`} type="button" onClick={() => onPickMention(e2)}
                className="block w-full text-left px-3 py-2 hover:bg-surface-muted border-b border-border last:border-b-0">
                {e2.kind === 'component'
                  ? (
                    <div className="flex items-baseline gap-2">
                      <span className="shrink-0 text-[10px] font-mono uppercase text-primary bg-primary/10 rounded px-1 py-0.5">comp</span>
                      <span className="text-sm text-text font-medium truncate">{e2.label}</span>
                      <span className="ml-auto shrink-0 text-[11px] text-text-tertiary">{e2.count} node{e2.count === 1 ? '' : 's'}</span>
                    </div>
                  )
                  : (
                    <>
                      <div className="flex items-baseline gap-2">
                        <span className="shrink-0 text-[10px] font-mono uppercase text-text-secondary bg-surface-muted rounded px-1 py-0.5">{e2.nodeType || 'node'}</span>
                        <span className="text-sm text-text truncate">{e2.label}</span>
                        <span className="ml-auto shrink-0 text-[11px] text-text-tertiary truncate max-w-[45%]">in {e2.comp}</span>
                      </div>
                      {e2.snippet && (
                        <div className="text-[11px] text-text-tertiary truncate mt-0.5 pl-1">{e2.snippet}</div>
                      )}
                    </>
                  )}
              </button>
            ))}
          </div>
        )}
        <textarea ref={taRef} rows={1} value={value}
          onChange={(e) => { setDismissed(false); onChange(e.target.value); }}
          onInput={resize}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
          aria-label="Chat message"
          placeholder="Ask about or edit the dialogue…"
          className="flex-1 min-w-0 resize-none border border-border rounded-xl px-3 py-2 text-sm text-text bg-surface focus:outline-none focus:ring-2 focus:ring-primary"
          style={{ maxHeight: MAX_H }} />
        <input ref={fileInputRef} type="file" onChange={handleFileSelect} className="hidden" data-testid="file-input" accept="image/*,.xls,.xlsx,.json,.txt" multiple />
        <button type="button" onClick={() => fileInputRef.current?.click()} disabled={sending || attaching}
          className="shrink-0 h-[38px] w-[38px] flex items-center justify-center text-text-tertiary hover:text-text hover:bg-surface-muted rounded-lg transition-colors"
          title="Attach file" data-testid="attach-button">
          <Paperclip size={20} />
        </button>
        {sending
          ? <button type="button" onClick={onCancel} className="shrink-0 px-4 h-[38px] bg-error text-primary-fg rounded-xl hover:opacity-90">Stop</button>
          : <button type="submit" className="shrink-0 px-4 h-[38px] bg-primary text-primary-fg rounded-xl hover:bg-primary-hover">Send</button>}
      </div>
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-1 px-1" data-testid="image-chip">
          {images.map((im, i) => (
            <span key={i} className="relative inline-block">
              <img src={im.url} alt={im.name} className="h-12 w-12 object-cover rounded border border-border" />
              <button type="button" onClick={() => { clearImage(i).catch(err => console.error('clear image failed:', err)); setImages((xs) => xs.filter((_, j) => j !== i)); }}
                className="absolute -top-1 -right-1 bg-surface rounded-full text-text-tertiary hover:text-text">
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
      {!canSendImages && (
        <div className="text-[11px] text-text-tertiary mt-0.5 px-1" data-testid="no-vision-hint">
          Current model can't read images — pick a Claude vision model in Settings.
        </div>
      )}
      {attachment
        ? (
          <div className="text-[11px] text-text-tertiary mt-1 px-1 flex items-center gap-2">
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
        )
        : images.length === 0 && <div className="text-[11px] text-text-tertiary mt-1 px-1">Enter to send · Shift+Enter for newline</div>}
    </form>
  );
}
