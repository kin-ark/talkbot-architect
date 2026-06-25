import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ToolChip from './ToolChip';
import DiffCard from './DiffCard';

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

export default function ChatPane({ transcript, proposal, sending, onSend, onApply, onReject, onCancel, onPreview, summary, onSelectNode }) {
  const [input, setInput] = useState('');
  const submit = (e) => { e.preventDefault(); if (!input.trim()) return; onSend(input.trim()); setInput(''); };
  const slashMatches = input.startsWith('/')
    ? SLASH.filter((c) => c.cmd.startsWith(input.split(' ')[0].toLowerCase()))
    : [];
  const pickSlash = (c) => {
    if (c.mode === 'send') { onSend(c.text); setInput(''); }
    else { setInput(c.text); }
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
  };
  return (
    <div className="flex flex-col h-full" data-testid="chat-pane">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {transcript.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            {m.tool_trace?.length > 0 && (
              <div className="mb-1">{m.tool_trace.map((t, j) => <ToolChip key={j} name={t.name} args={t.arguments} status={t.status} summary={t.summary} />)}</div>
            )}
            <div className={`inline-block max-w-[80%] p-3 rounded-2xl text-sm ${bubbleClass(m.role)} ${m.role === 'user' || m.role === 'error' ? 'whitespace-pre-wrap' : 'prose prose-sm max-w-none prose-pre:bg-surface-muted prose-pre:text-text'}`}>
              {m.role === 'user' || m.role === 'error'
                ? m.text
                : <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{m.text || ''}</ReactMarkdown>}
            </div>
          </div>
        ))}
        {sending && (
          <div className="text-left" data-testid="thinking">
            <span className="inline-block p-3 rounded-2xl text-sm bg-surface border border-border text-text-tertiary">thinking…</span>
          </div>
        )}
        {proposal && <DiffCard proposal={proposal} onApply={onApply} onReject={onReject} onPreview={onPreview} />}
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
