import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import DiffCard from './DiffCard';

describe('DiffCard', () => {
  it('renders delta and fires onApply', () => {
    const onApply = vi.fn();
    render(<DiffCard proposal={{ diff: '- a\n+ b', checker_delta: { errors_after: 0, errors_before: 0, new_error_codes: [] } }} onApply={onApply} onReject={() => {}} />);
    fireEvent.click(screen.getByText('Apply'));
    expect(onApply).toHaveBeenCalled();
  });
});
