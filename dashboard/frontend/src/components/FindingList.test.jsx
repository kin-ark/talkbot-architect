import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import FindingList from './FindingList';

describe('FindingList', () => {
  it('groups by severity and fires onSelect with node id', () => {
    const onSelect = vi.fn();
    render(<FindingList findings={[{ code: 'WIZ101', severity: 'error', message: 'dead end', entity: 'FlowNode', id: 'n9' }]} onSelect={onSelect} />);
    expect(screen.getByText(/Errors/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/WIZ101/));
    expect(onSelect).toHaveBeenCalledWith({ uuid: 'n9' });
  });
});
