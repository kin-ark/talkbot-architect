import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MessageBubble from './MessageBubble';

describe('WaitingHeader retry + nudge', () => {
  it('shows provider-busy retry line when status is retrying', () => {
    render(<MessageBubble role="agent" text="" isLast sending
      toolTrace={[]} status={{ kind: 'retrying', attempt: 2, attempts: 3 }} />);
    expect(screen.getByText(/retrying \(2\/3\)/i)).toBeInTheDocument();
  });
  it('shows the long-run nudge past 90s', () => {
    vi.useFakeTimers();
    render(<MessageBubble role="agent" text="" isLast sending toolTrace={[]} />);
    act(() => { vi.advanceTimersByTime(91000); });
    expect(screen.getByText(/taking longer than usual/i)).toBeInTheDocument();
    vi.useRealTimers();
  });
});
