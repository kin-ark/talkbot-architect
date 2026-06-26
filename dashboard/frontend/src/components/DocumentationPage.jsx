import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { helpTopics } from '../help/helpTopics';

export default function DocumentationPage() {
  const [topicId, setTopicId] = useState(helpTopics[0].id);
  const topic = helpTopics.find((t) => t.id === topicId) || helpTopics[0];
  return (
    <div data-testid="documentation-page" className="flex gap-4 min-h-[20rem]">
      <nav className="w-44 shrink-0 space-y-0.5">
        {helpTopics.map((t) => {
          const active = t.id === topicId;
          return (
            <button type="button" key={t.id} onClick={() => setTopicId(t.id)}
              className={`w-full text-left rounded-md px-2.5 py-1.5 text-sm ${
                active ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted'}`}>
              {t.title}
            </button>
          );
        })}
      </nav>
      <div data-testid="doc-content"
        className="flex-1 min-w-0 prose prose-sm dark:prose-invert max-w-none text-text">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{topic.body}</ReactMarkdown>
      </div>
    </div>
  );
}
