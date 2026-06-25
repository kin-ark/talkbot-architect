import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DiffCard from './DiffCard';

const PROPOSAL = {
  diff: '--- current\n+++ proposed\n+added line',
  checker_delta: { errors_before: 0, errors_after: 0, warnings_before: 0, warnings_after: 0 },
  change_summary: 'Adds 1 component · 2 nodes added · ✓ 0 new errors',
  proposed_summary: { components: [], knowledge_bases: [] },
  change_set: { added_components: ['cA'], added_nodes: ['n1', 'n2'], changed_nodes: [], removed_nodes: [], removed_components: [] },
};

describe('DiffCard', () => {
  it('shows the plain-language change summary', () => {
    render(<DiffCard proposal={PROPOSAL} onApply={() => {}} onReject={() => {}} onPreview={() => {}} />);
    expect(screen.getByText(/Adds 1 component/)).toBeInTheDocument();
  });
  it('hides the raw diff behind a collapsed details element', () => {
    render(<DiffCard proposal={PROPOSAL} onApply={() => {}} onReject={() => {}} onPreview={() => {}} />);
    const details = screen.getByTestId('diff-details');
    expect(details.open).toBe(false);            // collapsed by default
    expect(details.textContent).toMatch(/added line/);
  });
  it('Preview in graph fires onPreview with the proposal', () => {
    const onPreview = vi.fn();
    render(<DiffCard proposal={PROPOSAL} onApply={() => {}} onReject={() => {}} onPreview={onPreview} />);
    fireEvent.click(screen.getByText(/preview in graph/i));
    expect(onPreview).toHaveBeenCalledWith(PROPOSAL);
  });
  it('Apply and Reject still fire', () => {
    const onApply = vi.fn(); const onReject = vi.fn();
    render(<DiffCard proposal={PROPOSAL} onApply={onApply} onReject={onReject} onPreview={() => {}} />);
    fireEvent.click(screen.getByText('Apply')); fireEvent.click(screen.getByText('Reject'));
    expect(onApply).toHaveBeenCalled(); expect(onReject).toHaveBeenCalled();
  });
});
