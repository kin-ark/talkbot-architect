import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { proposal: null, sending: false, onSend: () => {}, onApply: () => {},
  onReject: () => {}, onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

describe('ChatPane inline node links', () => {
  it('renders a #node: markdown link as a clickable that calls onSelectNode', () => {
    const onSelectNode = vi.fn();
    const transcript = [{ role: 'agent', text: 'See [Greeting](#node:abc-123) for details.' }];
    render(<ChatPane {...base} transcript={transcript} onSelectNode={onSelectNode} />);
    fireEvent.click(screen.getByText('Greeting'));
    expect(onSelectNode).toHaveBeenCalledWith({ uuid: 'abc-123' });
  });

  it('renders a normal link as a plain anchor (not a node click)', () => {
    const onSelectNode = vi.fn();
    const transcript = [{ role: 'agent', text: 'Docs at [here](https://example.com).' }];
    render(<ChatPane {...base} transcript={transcript} onSelectNode={onSelectNode} />);
    const link = screen.getByText('here');
    expect(link.tagName).toBe('A');
    fireEvent.click(link);
    expect(onSelectNode).not.toHaveBeenCalled();
  });
});
