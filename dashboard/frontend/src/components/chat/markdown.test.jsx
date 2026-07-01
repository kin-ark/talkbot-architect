import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { makeMdComponents } from './markdown';

function md(text, onSelectNode = () => {}) {
  return render(
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={makeMdComponents(onSelectNode)}>{text}</ReactMarkdown>
  );
}

describe('makeMdComponents', () => {
  it('renders a #node: link as a button that calls onSelectNode', () => {
    const onSelectNode = vi.fn();
    md('[GreetNode](#node:abc-123)', onSelectNode);
    fireEvent.click(screen.getByText('GreetNode'));
    expect(onSelectNode).toHaveBeenCalledWith({ uuid: 'abc-123' });
  });

  it('wraps tables in a horizontal scroll container', () => {
    md('| a | b |\n|---|---|\n| 1 | 2 |');
    expect(screen.getByTestId('md-table-scroll')).toBeInTheDocument();
  });

  it('renders blockquote, hr, and a heading', () => {
    const { container } = md('# Title\n\n> quote\n\n---\n');
    expect(container.querySelector('blockquote')).not.toBeNull();
    expect(container.querySelector('hr')).not.toBeNull();
    expect(screen.getByText('Title')).toBeInTheDocument();
  });

  it('block code renders with a copy button', () => {
    md('```js\nconst x = 1;\n```');
    expect(screen.getByTestId('copy-code')).toBeInTheDocument();
  });
});
