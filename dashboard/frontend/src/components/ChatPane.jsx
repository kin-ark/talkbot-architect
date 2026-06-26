import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import ToolChip from './ToolChip';
import DiffCard from './DiffCard';

function extractText(node) {
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (node?.props?.children) return extractText(node.props.children);
  return '';
}

function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    const text = extractText(children);
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }).catch(() => {});
  };
  return (
    <div className="relative my-2 rounded-lg overflow-hidden" style={{ background: 'var(--c-code-bg)', color: 'var(--c-code-fg)' }}>
      <button type="button" onClick={copy} data-testid="copy-code"
        className="absolute top-1.5 right-1.5 text-xs px-2 py-0.5 rounded bg-black/30 text-white/80 hover:bg-black/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
        {copied ? 'Copied' : 'Copy'}
      </button>
      <pre className="overflow-x-auto p-3 text-[0.8rem] leading-relaxed m-0">{children}</pre>
    </div>
  );
}

function mentionEntries(summary) {
  const out = [];
  for (const c of summary?.components || []) {
    out.push({ kind: 'component', label: c.name, uuid: c.uuid });
    for (const n of Object.values(c.nodes || {})) {
      out.push({ kind: 'node', label: n.label || n.uuid, uuid: n.uuid });
    }
  }
  return out;
}

const SLASH = [
  { cmd: '/validate', mode: 'send', text: 'Validate the dialogue and list all findings.' },
  { cmd: '/explain', mode: 'send', text: 'Explain what this bot does, step by step.' },
  { cmd: '/summary', mode: 'send', text: 'Summarize the dialogue flow.' },
  { cmd: '/add-node', mode: 'fill', text: 'Add a node: ' },
  { cmd: '/add-component', mode: 'fill', text: 'Add a component named ' },
];

const SUGGESTIONS = [
  { label: 'Validate', prompt: 'Validate the dialogue and list all findings.' },
  { label: 'Explain this bot', prompt: 'Explain what this bot does, step by step.' },
  { label: 'Find problems', prompt: 'Find problems or issues in this dialogue.' },
  { label: 'Suggest improvements', prompt: 'Suggest improvements to this dialogue.' },
];

function ChipRow({ onSend }) {
  return (
    <div className="flex flex-wrap gap-2" data-testid="suggestion-chips">
      {SUGGESTIONS.map((s) => (
        <button key={s.label} type="button" onClick={() => onSend(s.prompt)}
          className="text-xs rounded-full border border-border px-3 py-1 text-text-secondary hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
          {s.label}
        </button>
      ))}
    </div>
  );
}

function bubbleClass(role) {
  if (role === 'user') return 'bg-primary text-primary-fg';
  if (role === 'error') return 'bg-error-bg border border-error text-error';
  return 'bg-surface border border-border text-text';
}

export default function ChatPane({ transcript, proposal, sending, onSend, onRetry, onApply, onReject, onCancel, onPreview, summary, onSelectNode, canUndo = false, canRedo = false, onUndo, onRedo }) {
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);
  const nearBottomRef = useRef(true);
  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    nearBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };
  useEffect(() => {
    const el = scrollRef.current;
    if (el && nearBottomRef.current) el.scrollTop = el.scrollHeight;
  }, [transcript]);
  const submit = (e) => { e.preventDefault(); if (!input.trim()) return; onSend(input.trim()); setInput(''); };
  const slashMatches = input.startsWith('/')
    ? SLASH.filter((c) => c.cmd.startsWith(input.split(' ')[0].toLowerCase()))
    : [];
  const pickSlash = (c) => {
    if (c.mode === 'send') { onSend(c.text); setInput(''); }
    else { setInput(c.text); }
  };
  const mentionMatch = input.startsWith('/') ? null : input.match(/@(\S*)$/);  // trailing @token; suppressed inside a slash command
  const mentionQuery = mentionMatch ? mentionMatch[1].toLowerCase() : null;
  const mentionMatches = mentionQuery !== null
    ? mentionEntries(summary).filter((e) => e.label.toLowerCase().includes(mentionQuery)).slice(0, 8)
    : [];
  const pickMention = (e) => {
    setInput(input.replace(/@(\S*)$/, `@${e.label} (${e.uuid}) `));
  };
  const mdComponents = {
    a: ({ href, children }) => {
      if (typeof href === 'string' && href.startsWith('#node:')) {
        const uuid = href.slice(6);            // '#node:'.length === 6
        return (
          <button type="button" onClick={() => onSelectNode?.({ uuid })}
            className="text-primary underline hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
            {children}
          </button>
        );
      }
      return <a href={href} target="_blank" rel="noreferrer" className="text-primary underline">{children}</a>;
    },
    table: ({ children }) => (
      <div className="overflow-x-auto my-2" data-testid="md-table-scroll">
        <table className="w-full text-sm border border-border">{children}</table>
      </div>
    ),
    th: ({ children }) => <th className="border border-border bg-surface-muted px-2 py-1 text-left">{children}</th>,
    td: ({ children }) => <td className="border border-border px-2 py-1 align-top">{children}</td>,
    code: ({ inline, className, children, ...props }) => {
      // Block code (fenced) carries a language- className and is handled by `pre`'s child;
      // render it untouched so the `pre` renderer (Task 2) + rehype-highlight classes survive.
      if (className || inline === false) {
        return <code className={className} {...props}>{children}</code>;
      }
      return <code className="font-mono text-[0.85em] bg-surface-muted text-text rounded px-1 py-0.5">{children}</code>;
    },
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  };
  return (
    <div className="flex flex-col h-full" data-testid="chat-pane">
      <div ref={scrollRef} onScroll={onScroll} className="flex-1 overflow-y-auto p-4 space-y-3">
        {transcript.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            {m.tool_trace?.length > 0 && (
              <div className="mb-1">{m.tool_trace.map((t, j) => <ToolChip key={j} name={t.name} args={t.arguments} status={t.status} summary={t.summary} />)}</div>
            )}
            <div className={`inline-block max-w-[80%] p-3 rounded-2xl text-sm ${bubbleClass(m.role)} ${m.role === 'user' || m.role === 'error' ? 'whitespace-pre-wrap' : 'prose prose-sm dark:prose-invert max-w-none prose-pre:p-0 prose-pre:bg-transparent'}`}>
              {m.role === 'user' || m.role === 'error'
                ? m.text
                : <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={mdComponents}>{m.text || ''}</ReactMarkdown>}
              {m.role !== 'user' && m.role !== 'error' && sending && i === transcript.length - 1 && (
                <span data-testid="stream-caret" className="inline-block w-1.5 animate-pulse">▍</span>
              )}
            </div>
            {m.role === 'error' && (
              <div className="mt-1">
                <button type="button" onClick={onRetry}
                  className="text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">Retry</button>
              </div>
            )}
            {m.role === 'agent' && typeof m.text === 'string' && m.text.includes('tool-iteration limit') && (
              <div className="mt-1">
                <button type="button" onClick={() => onSend('continue')}
                  className="text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">Continue</button>
              </div>
            )}
          </div>
        ))}
        {transcript.length > 0 && transcript[transcript.length - 1].role === 'agent' && (
          <div className="text-left">
            <button type="button" onClick={onRetry}
              className="text-xs text-text-tertiary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">↻ Regenerate</button>
          </div>
        )}
        {sending && !(transcript.length > 0 && transcript[transcript.length - 1].role === 'agent') && (
          <div className="text-left" data-testid="thinking">
            <span className="inline-block p-3 rounded-2xl text-sm bg-surface border border-border text-text-tertiary">thinking…</span>
          </div>
        )}
        {proposal && <DiffCard proposal={proposal} onApply={onApply} onReject={onReject} onPreview={onPreview} />}
      </div>
      <div className="px-4 pb-1 flex gap-2" data-testid="chat-undo-row">
          <button type="button" onClick={onUndo} disabled={!canUndo}
            className="text-xs text-text-secondary disabled:opacity-40 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">↶ Undo</button>
          <button type="button" onClick={onRedo} disabled={!canRedo}
            className="text-xs text-text-secondary disabled:opacity-40 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">↷ Redo</button>
        </div>
      <div className="px-4 pb-2"><ChipRow onSend={onSend} /></div>
      <form onSubmit={submit} data-testid="chat-form" className="p-4 border-t border-border bg-surface">
        <div className="relative flex gap-2">
          {slashMatches.length > 0 && (
            <div data-testid="slash-menu"
              className="absolute bottom-full mb-1 left-0 w-72 rounded-lg border border-border bg-surface shadow-card overflow-hidden z-30">
              {slashMatches.map((c) => (
                <button key={c.cmd} type="button" onClick={() => pickSlash(c)}
                  className="block w-full text-left px-3 py-1.5 text-sm text-text hover:bg-surface-muted">
                  <span className="font-mono text-primary">{c.cmd}</span>
                  <span className="text-text-tertiary"> — {c.text.trim() || '…'}</span>
                </button>
              ))}
            </div>
          )}
          {mentionMatches.length > 0 && (
            <div data-testid="mention-menu"
              className="absolute bottom-full mb-1 left-0 w-72 max-h-60 overflow-y-auto rounded-lg border border-border bg-surface shadow-card z-30">
              {mentionMatches.map((e) => (
                <button key={`${e.kind}-${e.uuid}`} type="button" onClick={() => pickMention(e)}
                  className="block w-full text-left px-3 py-1.5 text-sm text-text hover:bg-surface-muted">
                  <span className="text-text-tertiary text-xs uppercase mr-2">{e.kind === 'component' ? 'comp' : 'node'}</span>
                  {e.label}
                </button>
              ))}
            </div>
          )}
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about or edit the dialogue…"
            className="flex-1 border border-border rounded-xl px-3 py-2 text-sm text-text bg-surface focus:outline-none focus:ring-2 focus:ring-primary" />
          {sending
            ? <button type="button" onClick={onCancel} className="px-4 bg-error text-primary-fg rounded-xl hover:opacity-90">Stop</button>
            : <button type="submit" className="px-4 bg-primary text-primary-fg rounded-xl hover:bg-primary-hover">Send</button>}
        </div>
      </form>
    </div>
  );
}
