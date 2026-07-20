import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProgressBar from './ProgressBar';

describe('ProgressBar', () => {
  it('determinate: sets aria-valuenow and fill width', () => {
    render(<ProgressBar value={42} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '42');
    expect(screen.getByTestId('progress-fill').style.width).toBe('42%');
  });
  it('indeterminate: renders the animated variant without a numeric value', () => {
    render(<ProgressBar value={null} />);
    expect(screen.getByTestId('progress-indeterminate')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).not.toHaveAttribute('aria-valuenow');
  });
});
