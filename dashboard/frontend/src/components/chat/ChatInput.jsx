import { useRef, useState, useLayoutEffect, useEffect } from 'react';
import { Paperclip, X } from 'lucide-react';
import { attachFile, clearAttachment, clearImage } from '../../api';
import { toast } from '../../toast/toastStore';

const MAX_H = 144; // ~6 lines
const MAX_IMAGES = 4;                       // matches the backend cap
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;    // 5 MB, matches the backend cap

export default function ChatInput({ value, onChange, onSubmit, sending, onCancel,
  slashMatches, mentionMatches, onPickSlash, onPickMention, canSendImages = true }) {
  const taRef = useRef(null);
  const fileInputRef = useRef(null);
  const [dismissed, setDismissed] = useState(false);
  const [attachment, setAttachment] = useState(null);
  const [attaching, setAttaching] = useState(false);
  const [progress, setProgress] = useState(null);   // 0-100 while an attach uploads
  const [images, setImages] = useState([]);

  // Revoke object URLs for any STILL-STAGED (unsent) images on unmount — sent
  // images clear `images` (ownership transfers to the bubble) so nothing leaks.
  const imagesRef = useRef([]);
  useEffect(() => { imagesRef.current = images; }, [images]);
  useEffect(() => () => imagesRef.current.forEach((im) => URL.revokeObjectURL(im.url)), []);

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
    // Allow text-only, image-only, or file-only.
    if ((!value.trim() && images.length === 0 && !attachment) || sending) return;
    onSubmit({ text: value, images, attachment });
    setAttachment(null);
    setImages([]);   // clear chips; ownership of the object URLs transfers to the sent bubble — do NOT revoke here
  };

  // Returns false (and toasts) if adding this image would exceed the count/size
  // caps. `staged` is the count already accepted this batch (state lags in a loop).
  const imageAllowed = (file, staged) => {
    if (staged >= MAX_IMAGES) {
      toast.error(`You can attach at most ${MAX_IMAGES} images per message.`);
      return false;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      toast.error(`Image too large (max 5 MB): ${file.name}`);
      return false;
    }
    return true;
  };

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (!files) return;
    setAttaching(true);
    setProgress(0);
    let staged = images.length;
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.type.startsWith('image/')) {
          // Don't upload images on a non-vision model — they'd only 400 on send.
          if (!canSendImages) continue;
          if (!imageAllowed(file, staged)) continue;
        }
        setProgress(0);
        const result = await attachFile(file, setProgress);
        if (result.kind === 'image') {
          staged += 1;
          setImages((xs) => [...xs, { name: result.name, url: URL.createObjectURL(file) }]);
        } else {
          setAttachment(result);
        }
      }
    } catch (err) {
      console.error('attach failed:', err);
      toast.error('Attachment failed. Please try again.');
    } finally {
      setAttaching(false);
      setProgress(null);
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
    setProgress(0);
    let staged = images.length;
    try {
      for (const it of imgs) {
        const f = it.getAsFile();
        if (!f || !imageAllowed(f, staged)) continue;
        try {
          setProgress(0);
          const r = await attachFile(f, setProgress);
          if (r.kind === 'image') {
            staged += 1;
            setImages((xs) => [...xs, { name: r.name, url: URL.createObjectURL(f) }]);
          }
        } catch (err) {
          console.error('attach failed:', err);
          toast.error('Pasting the image failed. Please try again.');
        }
      }
    } finally {
      setAttaching(false);
      setProgress(null);
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
          title="Attach file" aria-label="Attach file" data-testid="attach-button">
          <Paperclip size={20} />
        </button>
        {sending
          ? <button type="button" onClick={onCancel} className="shrink-0 px-4 h-[38px] bg-error text-primary-fg rounded-xl hover:opacity-90">Stop</button>
          : <button type="submit" className="shrink-0 px-4 h-[38px] bg-primary text-primary-fg rounded-xl hover:bg-primary-hover">Send</button>}
      </div>
      {attaching && (
        <div className="mt-1.5 px-1" data-testid="attach-progress">
          <div className="h-1 w-full rounded-full bg-surface-muted overflow-hidden">
            <div className={`h-full bg-primary transition-all duration-150 ${progress == null ? 'animate-pulse' : ''}`}
              style={{ width: progress == null ? '100%' : `${progress}%` }} />
          </div>
          <div className="text-[11px] text-text-tertiary mt-0.5">
            {progress == null ? 'Uploading attachment…' : `Uploading attachment… ${progress}%`}
          </div>
        </div>
      )}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-1 px-1" data-testid="image-chip">
          {images.map((im, i) => (
            <span key={i} className="relative inline-block">
              <img src={im.url} alt={im.name} className="h-12 w-12 object-cover rounded border border-border" />
              <button type="button" aria-label={`Remove image ${im.name}`} onClick={async () => {
                try {
                  await clearImage(i);
                  URL.revokeObjectURL(im.url);
                  setImages((xs) => xs.filter((_, j) => j !== i));
                } catch {
                  toast.error('Could not remove the image — try again.');
                }
              }}
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
              <button type="button" onClick={async () => {
                try {
                  await clearAttachment();
                  setAttachment(null);
                } catch {
                  toast.error('Could not remove the file — try again.');
                }
              }} disabled={sending} aria-label="Remove attachment" className="p-0 text-text-tertiary hover:text-text">
                <X size={14} />
              </button>
            </span>
          </div>
        )
        : images.length === 0 && <div className="text-[11px] text-text-tertiary mt-1 px-1">Enter to send · Shift+Enter for newline</div>}
    </form>
  );
}
