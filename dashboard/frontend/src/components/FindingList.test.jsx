import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FindingList from './FindingList';

const FINDINGS = [
  { code: 'WIZ102', severity: 'error', message: 'orphan node', id: 'n1', entity: 'node' },
  { code: 'WIZ301', severity: 'warning', message: 'unused intent', id: 'i1', entity: 'intent' },
];

describe('FindingList', () => {
  it('groups by severity and fires onSelect with node id', () => {
    const onSelect = vi.fn();
    render(<FindingList findings={[{ code: 'WIZ101', severity: 'error', message: 'dead end', entity: 'FlowNode', id: 'n9' }]} onSelect={onSelect} onAskFix={() => {}} />);
    expect(screen.getAllByText(/Errors/)[0]).toBeInTheDocument();
    fireEvent.click(screen.getByText(/WIZ101/));
    expect(onSelect).toHaveBeenCalledWith({ uuid: 'n9' });
  });

  it('severity filter hides the other group', () => {
    render(<FindingList findings={FINDINGS} onSelect={() => {}} onAskFix={() => {}} />);
    expect(screen.getByText(/WIZ102/)).toBeInTheDocument();
    expect(screen.getByText(/WIZ301/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^errors$/i }));
    expect(screen.getByText(/WIZ102/)).toBeInTheDocument();
    expect(screen.queryByText(/WIZ301/)).not.toBeInTheDocument();
  });

  it('Fix button calls onAskFix with the finding', () => {
    const onAskFix = vi.fn();
    render(<FindingList findings={FINDINGS} onSelect={() => {}} onAskFix={onAskFix} />);
    fireEvent.click(screen.getAllByRole('button', { name: /fix/i })[0]);
    expect(onAskFix).toHaveBeenCalledWith(expect.objectContaining({ code: 'WIZ102' }));
  });

  it('activates a finding row via keyboard', () => {
    const onSelect = vi.fn();
    render(<FindingList findings={[{ code: 'WIZ101', message: 'x', severity: 'error', id: 'n1' }]}
      onSelect={onSelect} onAskFix={() => {}} />);
    const row = screen.getByText(/WIZ101/).closest('[role="button"]');
    expect(row).toHaveAttribute('tabindex', '0');
    fireEvent.keyDown(row, { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledWith({ uuid: 'n1' });
  });
});
