import { useState, useMemo } from 'react';
import { ArrowDown } from 'lucide-react';
import DiffCard from './DiffCard';
import ChatInput from './chat/ChatInput';
import MessageBubble from './chat/MessageBubble';
import { makeMdComponents } from './chat/markdown';
import { useChatScroll } from './chat/useChatScroll';

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

export default function ChatPane({ transcript, proposal, sending, onSend, onRetry, onApply, onReject, onCancel, onPreview, summary, onSelectNode, canUndo = false, canRedo = false, onUndo, onRedo }) {
  const [input, setInput] = useState('');
  const { scrollRef, onScroll, atBottom, scrollToBottom } = useChatScroll(transcript);

  const submit = () => { if (!input.trim()) return; onSend(input.trim()); setInput(''); };

  const slashMatches = input.startsWith('/')
    ? SLASH.filter((c) => c.cmd.startsWith(input.split(' ')[0].toLowerCase()))
    : [];
  const pickSlash = (c) => { if (c.mode === 'send') { onSend(c.text); setInput(''); } else { setInput(c.text); } };

  const mentionMatch = input.startsWith('/') ? null : input.match(/@(\S*)$/);
  const mentionQuery = mentionMatch ? mentionMatch[1].toLowerCase() : null;
  const entries = useMemo(() => mentionEntries(summary), [summary]);
  const mentionMatches = mentionQuery !== null
    ? entries.filter((e) => e.label.toLowerCase().includes(mentionQuery)).slice(0, 8)
    : [];
  const pickMention = (e) => setInput(input.replace(/@(\S*)$/, `@${e.label} (${e.uuid}) `));

  const mdComponents = useMemo(() => makeMdComponents(onSelectNode), [onSelectNode]);
  const lastIdx = transcript.length - 1;

  return (
    <div className="flex flex-col h-full" data-testid="chat-pane">
      <div className="relative flex-1 min-h-0">
        <div ref={scrollRef} onScroll={onScroll} className="h-full overflow-y-auto p-4 space-y-3">
          {transcript.map((m, i) => (
            <MessageBubble key={i} role={m.role} text={m.text} toolTrace={m.tool_trace}
              isLast={i === lastIdx} sending={sending} mdComponents={mdComponents}
              onRetry={onRetry} onSend={onSend} />
          ))}
          {!sending && transcript.length > 0 && transcript[lastIdx].role === 'agent' && (
            <div className="text-left">
              <button type="button" onClick={onRetry}
                className="text-xs text-text-tertiary hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">↻ Regenerate</button>
            </div>
          )}
          {sending && !(transcript.length > 0 && transcript[lastIdx].role === 'agent') && (
            <div className="text-left" data-testid="thinking">
              <span className="inline-block p-3 rounded-2xl text-sm bg-surface border border-border text-text-tertiary">thinking…</span>
            </div>
          )}
          {proposal && <DiffCard proposal={proposal} onApply={onApply} onReject={onReject} onPreview={onPreview} />}
        </div>
        {!atBottom && (
          <button type="button" data-testid="scroll-bottom" onClick={scrollToBottom}
            className="absolute bottom-2 right-3 z-10 inline-flex items-center gap-1 text-xs rounded-full border border-border bg-surface shadow-card px-2.5 py-1 text-text-secondary hover:bg-surface-muted">
            <ArrowDown size={13} /> Jump to latest
          </button>
        )}
      </div>
      <div className="px-4 pb-1 flex gap-2" data-testid="chat-undo-row">
        <button type="button" onClick={onUndo} disabled={!canUndo}
          className="text-xs text-text-secondary disabled:opacity-40 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">↶ Undo</button>
        <button type="button" onClick={onRedo} disabled={!canRedo}
          className="text-xs text-text-secondary disabled:opacity-40 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">↷ Redo</button>
      </div>
      <div className="px-4 pb-2"><ChipRow onSend={onSend} /></div>
      <ChatInput value={input} onChange={setInput} onSubmit={submit} sending={sending} onCancel={onCancel}
        slashMatches={slashMatches} mentionMatches={mentionMatches}
        onPickSlash={pickSlash} onPickMention={pickMention} />
    </div>
  );
}
