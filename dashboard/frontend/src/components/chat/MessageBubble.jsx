import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Copy, Check, Brain, ChevronRight, Paperclip } from 'lucide-react';
import IconButton from '../ui/IconButton';
import ActivityTimeline from './ActivityTimeline';
import ErrorBubble from './ErrorBubble';
import RecoveryBar from './RecoveryBar';
import { narrate } from './narration';

const LABEL = { user: 'You', error: 'Error', agent: 'Assistant' };

function bubbleClass(role) {
  if (role === 'user') return 'bg-primary text-primary-fg';
  if (role === 'error') return 'bg-error-bg border border-error text-error';
  return 'bg-surface border border-border text-text';
}

const PROSE = 'prose prose-sm dark:prose-invert max-w-none break-words prose-pre:p-0 prose-pre:bg-transparent prose-p:my-1.5 prose-headings:mt-3 prose-headings:mb-1 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-ul:list-disc prose-ol:list-decimal';

function fmtElapsed(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function WaitingHeader({ toolTrace, hasText, status }) {
  const [sec, setSec] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setSec((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const running = toolTrace?.find((t) => t.status === 'running');
  const label = status?.kind === 'retrying'
    ? `Provider busy — retrying (${status.attempt}/${status.attempts})`
    : hasText ? 'Writing' : running ? narrate(running.name) : 'Thinking';
  return (
    <div data-testid="thinking-header" className="text-xs text-text-tertiary mb-1">
      <div className="flex items-center gap-1.5">
        <span className="inline-block animate-pulse" aria-hidden="true">◐</span>
        <span>{label}…</span>
        <span className="font-mono">{fmtElapsed(sec)}</span>
      </div>
      {sec > 90 && !hasText && (
        <div className="mt-0.5 text-text-tertiary text-xs">Taking longer than usual — you can Stop and retry.</div>
      )}
    </div>
  );
}

export default function MessageBubble({ role, text, toolTrace, reasoning, isLast, sending, mdComponents, onRetry, onSend, images, file, status, kind, recovery, stopReason, onContinue, onFix, onEdit, onDiscard }) {
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);
  const userToggled = useRef(false);
  const plain = role === 'user' || role === 'error';

  // Auto-open reasoning while still thinking (no answer yet); auto-collapse
  // once the answer starts — unless the user manually toggled it.
  useEffect(() => {
    if (userToggled.current) return;
    setOpen(Boolean(reasoning) && !text);
  }, [reasoning, text]);

  const toggle = () => { userToggled.current = true; setOpen((v) => !v); };

  const copy = () => {
    navigator.clipboard?.writeText(text || '').then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 1500);
    }).catch(() => {});
  };

  const showWaiting = !plain && isLast && sending && !text;

  if (role === 'error') return <ErrorBubble text={text} kind={kind} recovery={recovery}
    onRetry={onRetry} onContinue={onContinue} onFix={onFix} onEdit={onEdit} onDiscard={onDiscard} />;

  return (
    <div className={`group ${role === 'user' ? 'text-right' : 'text-left'}`}>
      <div className="text-xs text-text-tertiary mb-0.5">{LABEL[role] || 'Assistant'}</div>
      {showWaiting && <WaitingHeader toolTrace={toolTrace} hasText={Boolean(text)} status={status} />}
      {!plain && reasoning && (
        <div data-testid="reasoning-block" className="mb-1 text-left">
          <button type="button" data-testid="reasoning-toggle" onClick={toggle}
            className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
            <ChevronRight size={12} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
            <Brain size={12} />
            <span>Reasoning</span>
          </button>
          {open && (
            <div className="mt-1 max-h-48 overflow-y-auto whitespace-pre-wrap text-xs text-text-tertiary border-l-2 border-border pl-2">
              {reasoning}
            </div>
          )}
        </div>
      )}
      {toolTrace?.length > 0 && <ActivityTimeline trace={toolTrace} />}
      <div className={`relative inline-block max-w-[80%] p-3 rounded-2xl text-sm ${bubbleClass(role)} ${plain ? 'whitespace-pre-wrap' : PROSE}`}>
        {plain
          ? text
          : <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={mdComponents}>{text || ''}</ReactMarkdown>}
        {!plain && isLast && sending && text && (
          <span data-testid="stream-caret" className="inline-block w-1.5 animate-pulse" aria-hidden="true">▍</span>
        )}
        {images?.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {images.map((im, i) => (
              <a key={i} href={im.url} target="_blank" rel="noopener noreferrer" title={im.name}>
                <img src={im.url} alt={im.name}
                     className="h-24 w-24 object-cover rounded border border-border" />
              </a>
            ))}
          </div>
        )}
        {file && (
          <a href={file.url} target="_blank" rel="noopener noreferrer" download={file.name}
             className="mt-2 inline-flex items-center gap-1.5 text-xs underline decoration-dotted">
            <Paperclip size={12} /> {file.name}
          </a>
        )}
      </div>
      {!plain && text && (
        <span className="ml-1 align-top opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
          <IconButton label="Copy message" data-testid="copy-message" onClick={copy} className="h-6 w-6">
            {copied ? <Check size={13} /> : <Copy size={13} />}
          </IconButton>
        </span>
      )}
      {role === 'error' && (
        <div className="mt-1">
          <button type="button" onClick={onRetry}
            className="text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">Retry</button>
        </div>
      )}
      {role === 'agent' && stopReason === 'limit' && (
        <RecoveryBar tokens={['continue']} onContinue={onContinue || (() => onSend('continue'))} />
      )}
    </div>
  );
}
