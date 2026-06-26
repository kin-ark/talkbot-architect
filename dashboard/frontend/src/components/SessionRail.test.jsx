import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import SessionRail from './SessionRail';

const SESSIONS = [
  { id: 's1', name: 'Debt Collector', updated: 2, usage: {} },
  { id: 's2', name: 'Payment Reminder', updated: 1, usage: {} },
];
const USAGE = { input_tokens: 1200, output_tokens: 340, turns: 5, model: 'claude-x' };

function setup(over = {}) {
  const props = {
    sessions: SESSIONS, activeSessionId: 's1',
    onNew: vi.fn(), onSwitch: vi.fn(), onRename: vi.fn(), onDelete: vi.fn(),
    usage: USAGE, collapsed: false, onToggleCollapse: vi.fn(), ...over,
  };
  render(<SessionRail {...props} />);
  return props;
}

describe('SessionRail', () => {
  it('lists sessions and marks the active one', () => {
    setup();
    const rows = screen.getAllByTestId('session-row');
    expect(rows).toHaveLength(2);
    const active = screen.getByText('Debt Collector').closest('[data-testid="session-row"]');
    expect(active.className).toContain('font-semibold');
  });

  it('New fires onNew', () => {
    const p = setup();
    fireEvent.click(screen.getByTestId('rail-new'));
    expect(p.onNew).toHaveBeenCalled();
  });

  it('clicking a row fires onSwitch with its id', () => {
    const p = setup();
    fireEvent.click(screen.getByText('Payment Reminder'));
    expect(p.onSwitch).toHaveBeenCalledWith('s2');
  });

  it('rename: clicking the pencil opens an input that commits onRename', () => {
    const p = setup();
    const row = screen.getByText('Debt Collector').closest('[data-testid="session-row"]');
    fireEvent.click(within(row).getByLabelText(/rename/i));
    const input = within(row).getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Renamed Bot' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(p.onRename).toHaveBeenCalledWith('s1', 'Renamed Bot');
  });

  it('delete: confirm then fires onDelete', () => {
    const p = setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const row = screen.getByText('Payment Reminder').closest('[data-testid="session-row"]');
    fireEvent.click(within(row).getByLabelText(/delete/i));
    expect(p.onDelete).toHaveBeenCalledWith('s2');
    window.confirm.mockRestore();
  });

  it('delete: cancel does NOT fire onDelete', () => {
    const p = setup();
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const row = screen.getByText('Payment Reminder').closest('[data-testid="session-row"]');
    fireEvent.click(within(row).getByLabelText(/delete/i));
    expect(p.onDelete).not.toHaveBeenCalled();
    window.confirm.mockRestore();
  });

  it('shows a usage readout', () => {
    setup();
    expect(screen.getByTestId('rail-usage').textContent).toMatch(/1200/);
    expect(screen.getByTestId('rail-usage').textContent).toMatch(/5 turns/);
  });

  it('collapse toggle fires onToggleCollapse', () => {
    const p = setup();
    fireEvent.click(screen.getByTestId('rail-collapse'));
    expect(p.onToggleCollapse).toHaveBeenCalled();
  });

  it('collapsed rail still lists switchable rows and a New button', () => {
    const p = setup({ collapsed: true });
    fireEvent.click(screen.getByTestId('rail-new'));
    expect(p.onNew).toHaveBeenCalled();
    fireEvent.click(screen.getAllByTestId('session-row')[1]);
    expect(p.onSwitch).toHaveBeenCalledWith('s2');
  });
});
