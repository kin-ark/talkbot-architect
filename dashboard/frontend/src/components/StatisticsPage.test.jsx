import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatisticsPage from './StatisticsPage';

const USAGE = { input_tokens: 1200, output_tokens: 340, turns: 5, model: 'claude-x' };
const SESSIONS = [
  { id: 's1', name: 'Debt Collector', usage: { input_tokens: 1200, output_tokens: 340, turns: 5, model: 'claude-x' } },
  { id: 's2', name: 'Payment Reminder', usage: { input_tokens: 50, output_tokens: 20, turns: 1, model: 'gpt-y' } },
];

describe('StatisticsPage', () => {
  it('shows the active session model + token totals', () => {
    render(<StatisticsPage usage={USAGE} sessions={SESSIONS} activeSessionId="s1" />);
    expect(screen.getByTestId('statistics-page').textContent).toMatch(/claude-x/);
    expect(screen.getByTestId('statistics-page').textContent).toMatch(/1,200/);
    expect(screen.getByTestId('statistics-page').textContent).toMatch(/5 turns/);
  });
  it('lists every session in the table', () => {
    render(<StatisticsPage usage={USAGE} sessions={SESSIONS} activeSessionId="s1" />);
    expect(screen.getByText('Payment Reminder')).toBeInTheDocument();
    expect(screen.getByText('gpt-y')).toBeInTheDocument();
  });
  it('handles no sessions / no usage', () => {
    render(<StatisticsPage usage={null} sessions={[]} activeSessionId={null} />);
    expect(screen.getByText(/No sessions yet/i)).toBeInTheDocument();
  });
});
