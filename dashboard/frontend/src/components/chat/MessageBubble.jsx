import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Copy, Check } from 'lucide-react';
import IconButton from '../ui/IconButton';
import ToolTrace from './ToolTrace';

const LABEL = { user: 'You', error: 'Error', agent: 'Assistant' };

function bubbleClass(role) {
  if (role === 'user') return 'bg-primary text-primary-fg';
  if (role === 'error') return 'bg-error-bg border border-error text-error';
  return 'bg-surface border border-border text-text';
}

const PROSE = 'prose prose-sm dark:prose-invert max-w-none break-words prose-pre:p-0 prose-pre:bg-transparent prose-p:my-1.5 prose-headings:mt-3 prose-headings:mb-1 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-ul:list-disc prose-ol:list-decimal';

export default function MessageBubble({ role, text, toolTrace, isLast, sending, mdComponents, onRetry, onSend }) {
  const [copied, setCopied] = useState(false);
  const plain = role === 'user' || role === 'error';
  const copy = () => {
    navigator.clipboard?.writeText(text || '').then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 1500);
    }).catch(() => {});
  };
  return (
    <div className={`group ${role === 'user' ? 'text-right' : 'text-left'}`}>
      <div className="text-xs text-text-tertiary mb-0.5">{LABEL[role] || 'Assistant'}</div>
      {toolTrace?.length > 0 && <ToolTrace trace={toolTrace} />}
      <div className={`relative inline-block max-w-[80%] p-3 rounded-2xl text-sm ${bubbleClass(role)} ${plain ? 'whitespace-pre-wrap' : PROSE}`}>
        {plain
          ? text
          : <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={mdComponents}>{text || ''}</ReactMarkdown>}
        {!plain && isLast && sending && (
          <span data-testid="stream-caret" className="inline-block w-1.5 animate-pulse">▍</span>
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
      {role === 'agent' && typeof text === 'string' && text.includes('tool-iteration limit') && (
        <div className="mt-1">
          <button type="button" onClick={() => onSend('continue')}
            className="text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">Continue</button>
        </div>
      )}
    </div>
  );
}
