import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import TopBar from './TopBar';

describe('TopBar', () => {
  it('disables undo when canUndo is false and fires onExport', () => {
    const onExport = vi.fn();
    render(<TopBar canUndo={false} canRedo onUndo={() => {}} onRedo={() => {}} onExport={onExport} onNew={() => {}} />);
    expect(screen.getByText('Undo').closest('button')).toBeDisabled();
    fireEvent.click(screen.getByText('Export'));
    expect(onExport).toHaveBeenCalled();
  });
});
