import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { proposal: null, sending: false, onApply: () => {}, onReject: vi.fn(),
  onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

describe('ChatPane recovery', () => {
  it('error entry renders RecoveryBar and Retry calls onRetry', () => {
    const onRetry = vi.fn();
    render(<ChatPane {...base} transcript={[{ role: 'error', text: 'boom', kind: 'transient', recovery: ['retry'] }]}
      onSend={() => {}} onRetry={onRetry} />);
    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });
  it('proposal_blocked error offers Fix errors -> canned onSend', () => {
    const onSend = vi.fn();
    render(<ChatPane {...base} transcript={[{ role: 'error', text: 'blocked', kind: 'proposal_blocked', recovery: ['fix', 'discard'] }]}
      onSend={onSend} onRetry={() => {}} />);
    fireEvent.click(screen.getByText('Fix errors'));
    expect(onSend).toHaveBeenCalledWith(expect.stringMatching(/re-propose/i));
  });
  it('limit-stopped agent bubble offers Continue', () => {
    const onSend = vi.fn();
    render(<ChatPane {...base} transcript={[{ role: 'agent', text: 'partial', stop_reason: 'limit' }]}
      onSend={onSend} onRetry={() => {}} />);
    fireEvent.click(screen.getByText('Continue'));
    expect(onSend).toHaveBeenCalledWith('continue');
  });
});
