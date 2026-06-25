import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { proposal: null, sending: false, onApply: () => {}, onReject: () => {},
  onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

describe('ChatPane recovery', () => {
  it('error bubble shows Retry calling onRetry', () => {
    const onRetry = vi.fn();
    render(<ChatPane {...base} transcript={[{ role: 'error', text: 'boom' }]}
      onSend={() => {}} onRetry={onRetry} />);
    fireEvent.click(screen.getByText(/retry/i));
    expect(onRetry).toHaveBeenCalled();
  });
  it('shows Continue when the agent hit the tool-iteration limit', () => {
    const onSend = vi.fn();
    render(<ChatPane {...base} transcript={[{ role: 'agent', text: '(stopped after tool-iteration limit)' }]}
      onSend={onSend} onRetry={() => {}} />);
    fireEvent.click(screen.getByText(/continue/i));
    expect(onSend).toHaveBeenCalledWith('continue');
  });
});
