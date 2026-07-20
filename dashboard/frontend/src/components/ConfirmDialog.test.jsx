import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ConfirmDialog from './ConfirmDialog';

describe('ConfirmDialog focus', () => {
  it('danger dialog focuses Cancel, not the destructive button', () => {
    render(<ConfirmDialog title="Delete?" message="x" danger confirmLabel="Delete"
      onConfirm={() => {}} onCancel={() => {}} />);
    expect(screen.getByTestId('confirm-cancel')).toHaveFocus();
  });
  it('non-danger dialog focuses the confirm button', () => {
    render(<ConfirmDialog title="Save?" message="x" confirmLabel="Save"
      onConfirm={() => {}} onCancel={() => {}} />);
    expect(screen.getByTestId('confirm-ok')).toHaveFocus();
  });
});
