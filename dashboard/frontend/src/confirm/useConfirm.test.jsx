import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, renderHook } from '@testing-library/react';
import { ConfirmProvider, useConfirm } from './ConfirmProvider';

function Harness({ opts, onResult }) {
  const confirm = useConfirm();
  return <button onClick={async () => onResult(await confirm(opts))}>go</button>;
}

function setup(opts = { title: 'T', message: 'M' }) {
  const onResult = vi.fn();
  render(<ConfirmProvider><Harness opts={opts} onResult={onResult} /></ConfirmProvider>);
  fireEvent.click(screen.getByText('go'));
  return onResult;
}

describe('useConfirm', () => {
  it('shows the dialog and resolves true on confirm', async () => {
    const onResult = setup();
    await screen.findByTestId('confirm-dialog');
    fireEvent.click(screen.getByTestId('confirm-ok'));
    await waitFor(() => expect(onResult).toHaveBeenCalledWith(true));
    expect(screen.queryByTestId('confirm-dialog')).toBeNull();
  });

  it('resolves false on cancel', async () => {
    const onResult = setup();
    await screen.findByTestId('confirm-dialog');
    fireEvent.click(screen.getByTestId('confirm-cancel'));
    await waitFor(() => expect(onResult).toHaveBeenCalledWith(false));
  });

  it('resolves false on Escape', async () => {
    const onResult = setup();
    await screen.findByTestId('confirm-dialog');
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => expect(onResult).toHaveBeenCalledWith(false));
  });

  it('applies danger styling to the confirm button', async () => {
    setup({ title: 'Del', message: 'sure?', danger: true });
    const ok = await screen.findByTestId('confirm-ok');
    expect(ok.className).toContain('bg-error');
  });

  it('resolves only once (Escape after a click does not double-fire)', async () => {
    const onResult = setup();
    await screen.findByTestId('confirm-dialog');
    fireEvent.click(screen.getByTestId('confirm-ok'));
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => expect(onResult).toHaveBeenCalledTimes(1));
  });

  it('falls back to window.confirm with no provider', async () => {
    const spy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const onResult = vi.fn();
    render(<Harness opts={{ title: 'T', message: 'M' }} onResult={onResult} />);
    fireEvent.click(screen.getByText('go'));
    await waitFor(() => expect(onResult).toHaveBeenCalledWith(true));
    expect(spy).toHaveBeenCalled();
    spy.mockRestore();
  });
});
