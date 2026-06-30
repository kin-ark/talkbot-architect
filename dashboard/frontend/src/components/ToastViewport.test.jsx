import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, within, act } from '@testing-library/react';
import ToastViewport from './ToastViewport';
import { toast, getSnapshot, dismiss } from '../toast/toastStore';

beforeEach(() => { act(() => { getSnapshot().slice().forEach((t) => dismiss(t.id)); }); });

describe('ToastViewport', () => {
  it('renders nothing when there are no toasts', () => {
    const { container } = render(<ToastViewport />);
    expect(container.querySelectorAll('[data-testid="toast"]').length).toBe(0);
  });

  it('renders a toast per kind with the right data-kind', () => {
    render(<ToastViewport />);
    act(() => { toast.success('ok'); toast.error('bad'); });
    const toasts = screen.getAllByTestId('toast');
    expect(toasts.length).toBe(2);
    expect(screen.getByText('ok').closest('[data-testid="toast"]').getAttribute('data-kind')).toBe('success');
    expect(screen.getByText('bad').closest('[data-testid="toast"]').getAttribute('data-kind')).toBe('error');
  });

  it('dismiss button removes the toast', () => {
    render(<ToastViewport />);
    act(() => { toast.info('dismiss me', { duration: 0 }); });
    const row = screen.getByText('dismiss me').closest('[data-testid="toast"]');
    fireEvent.click(within(row).getByTestId('toast-dismiss'));
    expect(screen.queryByText('dismiss me')).toBeNull();
  });
});
