/* eslint-disable react-refresh/only-export-components -- shared markdown helpers + component factory, not a fast-refresh boundary */
import { useState } from 'react';

export function extractText(node) {
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (node?.props?.children) return extractText(node.props.children);
  return '';
}

export function CodeBlock({ children }) {
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

export function makeMdComponents(onSelectNode) {
  return {
    a: ({ href, children }) => {
      if (typeof href === 'string' && href.startsWith('#node:')) {
        const uuid = href.slice(6);
        return (
          <button type="button" onClick={() => onSelectNode?.({ uuid })}
            className="text-primary underline hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
            {children}
          </button>
        );
      }
      return <a href={href} target="_blank" rel="noreferrer" className="text-primary underline break-words">{children}</a>;
    },
    table: ({ children }) => (
      <div className="overflow-x-auto my-2" data-testid="md-table-scroll">
        <table className="w-full text-sm border border-border">{children}</table>
      </div>
    ),
    th: ({ children }) => <th className="border border-border bg-surface-muted px-2 py-1 text-left">{children}</th>,
    td: ({ children }) => <td className="border border-border px-2 py-1 align-top">{children}</td>,
    blockquote: ({ children }) => <blockquote className="border-l-2 border-border pl-3 text-text-secondary italic my-2">{children}</blockquote>,
    h1: ({ children }) => <h1 className="text-base font-semibold mt-3 mb-1">{children}</h1>,
    h2: ({ children }) => <h2 className="text-base font-semibold mt-3 mb-1">{children}</h2>,
    h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>,
    hr: () => <hr className="my-3 border-border" />,
    code: ({ inline, className, children, ...props }) => {
      if (className || inline === false) {
        return <code className={className} {...props}>{children}</code>;
      }
      return <code className="font-mono text-[0.85em] bg-surface-muted text-text rounded px-1 py-0.5">{children}</code>;
    },
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  };
}
