import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MessageBubble from './MessageBubble';
import { makeMdComponents } from './markdown';

const md = makeMdComponents(() => {});
const base = { toolTrace: [], isLast: false, sending: false, mdComponents: md, onRetry: () => {}, onSend: () => {} };

describe('MessageBubble', () => {
  it('shows a sender label per role', () => {
    const { rerender } = render(<MessageBubble {...base} role="user" text="hi" />);
    expect(screen.getByText('You')).toBeInTheDocument();
    rerender(<MessageBubble {...base} role="agent" text="hi" />);
    expect(screen.getByText('Assistant')).toBeInTheDocument();
    rerender(<MessageBubble {...base} role="error" text="boom" />);
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('copy-message writes the raw text and shows a check', async () => {
    const writeText = vi.fn().mockResolvedValue();
    Object.assign(navigator, { clipboard: { writeText } });
    render(<MessageBubble {...base} role="agent" text="hello world" />);
    fireEvent.click(screen.getByTestId('copy-message'));
    expect(writeText).toHaveBeenCalledWith('hello world');
  });

  it('shows the stream caret on the last agent bubble while sending', () => {
    render(<MessageBubble {...base} role="agent" text="partial" isLast sending />);
    expect(screen.getByTestId('stream-caret')).toBeInTheDocument();
  });

  it('error bubble offers Retry', () => {
    const onRetry = vi.fn();
    render(<MessageBubble {...base} role="error" text="boom" onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('tool-iteration-limit agent text offers Continue', () => {
    const onSend = vi.fn();
    render(<MessageBubble {...base} role="agent" text="hit the tool-iteration limit" onSend={onSend} />);
    fireEvent.click(screen.getByText('Continue'));
    expect(onSend).toHaveBeenCalledWith('continue');
  });
});
