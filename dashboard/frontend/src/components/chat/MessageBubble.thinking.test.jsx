import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MessageBubble from './MessageBubble';
import { makeMdComponents } from './markdown';

const md = makeMdComponents(() => {});
const base = { toolTrace: [], isLast: false, sending: false, mdComponents: md, onRetry: () => {}, onSend: () => {} };

describe('MessageBubble thinking', () => {
  it('renders a Reasoning block when reasoning present', () => {
    render(<MessageBubble {...base} role="agent" text="answer" reasoning="because X" />);
    expect(screen.getByTestId('reasoning-block')).toBeInTheDocument();
    // With text present, reasoning auto-collapses; click to open
    fireEvent.click(screen.getByTestId('reasoning-toggle'));
    expect(screen.getByText(/because X/)).toBeInTheDocument();
  });

  it('does not render Reasoning when absent', () => {
    render(<MessageBubble {...base} role="agent" text="answer" />);
    expect(screen.queryByTestId('reasoning-block')).toBeNull();
  });

  it('shows the Thinking waiting header while sending with no answer yet', () => {
    render(<MessageBubble {...base} role="agent" text="" reasoning="" isLast sending />);
    expect(screen.getByTestId('thinking-header')).toHaveTextContent(/Thinking/);
  });

  it('reasoning block toggles collapsed on click', () => {
    render(<MessageBubble {...base} role="agent" text="answer" reasoning="deep" />);
    const toggle = screen.getByTestId('reasoning-toggle');
    // answer present → starts collapsed → body hidden
    expect(screen.queryByText('deep')).toBeNull();
    fireEvent.click(toggle);
    expect(screen.getByText('deep')).toBeInTheDocument();
  });
});
