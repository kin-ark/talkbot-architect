import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft } from 'lucide-react';
import { helpTopics } from '../help/helpTopics';
import { figures } from '../help/figures';

const FIG_RE = /^@@fig:([\w-]+)@@$/;

// Split a topic body into ordered segments: markdown chunks and figure refs.
function splitBody(body) {
  const segments = [];
  let buf = [];
  const flush = () => { if (buf.length) { segments.push({ type: 'md', text: buf.join('\n') }); buf = []; } };
  for (const line of body.split('\n')) {
    const m = line.match(FIG_RE);
    if (m) { flush(); segments.push({ type: 'fig', id: m[1] }); }
    else buf.push(line);
  }
  flush();
  return segments;
}

export default function DocsPage({ onClose }) {
  const [topicId, setTopicId] = useState(helpTopics[0].id);
  const topic = helpTopics.find((t) => t.id === topicId) || helpTopics[0];

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const segments = splitBody(topic.body);

  return (
    <div data-testid="docs-page" className="fixed inset-0 z-40 bg-canvas flex flex-col">
      <header className="h-12 shrink-0 border-b border-border bg-surface flex items-center gap-2 px-4">
        <img src="/favicon.svg" alt="" className="w-5 h-5 shrink-0" />
        <span className="text-sm font-semibold text-text">Documentation</span>
        <button type="button" data-testid="docs-back" onClick={onClose}
          className="ml-auto flex items-center gap-1 rounded-md px-2 py-1 text-sm text-text-secondary hover:bg-surface-muted hover:text-text">
          <ArrowLeft size={16} /> Back
        </button>
      </header>
      <div className="flex-1 flex overflow-hidden">
        <nav className="w-56 shrink-0 overflow-y-auto border-r border-border bg-surface p-2 space-y-0.5">
          {helpTopics.map((t) => {
            const Icon = t.icon;
            const active = t.id === topicId;
            return (
              <button type="button" key={t.id} onClick={() => setTopicId(t.id)}
                className={`w-full flex items-center gap-2 text-left rounded-md px-2.5 py-1.5 text-sm ${
                  active ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted'}`}>
                {Icon && <Icon size={16} className="shrink-0" />}
                <span className="truncate">{t.title}</span>
              </button>
            );
          })}
        </nav>
        <div className="flex-1 overflow-y-auto">
          <article data-testid="doc-content"
            className="max-w-3xl mx-auto px-8 py-8 prose prose-sm dark:prose-invert max-w-none text-text">
            {segments.map((seg, i) => {
              if (seg.type === 'md') {
                return <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>{seg.text}</ReactMarkdown>;
              }
              const Fig = figures[seg.id];
              return Fig ? <Fig key={i} /> : null;
            })}
          </article>
        </div>
      </div>
    </div>
  );
}
