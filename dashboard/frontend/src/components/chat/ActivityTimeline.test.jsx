import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ActivityTimeline from './ActivityTimeline';

describe('ActivityTimeline', () => {
  it('renders phase markers and tool rows in order', () => {
    const trace = [
      { _kind: 'tool', call_id: 'a', name: 'build', status: 'done', ts: 1, endTs: 4 },
      { _kind: 'phase', phase: 'fixing', round: 1, errors: 2, ts: 5 },
    ];
    render(<ActivityTimeline trace={trace} />);
    expect(screen.getByText(/Fixing 2 problems/)).toBeInTheDocument();
    expect(screen.getByText(/3\.0s/)).toBeInTheDocument(); // build elapsed
  });
  it('renders nothing for an empty trace', () => {
    const { container } = render(<ActivityTimeline trace={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
