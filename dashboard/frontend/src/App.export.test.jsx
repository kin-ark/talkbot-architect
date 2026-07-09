import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import * as api from './api';
import { useSession } from './state/useSession';
import { ConfirmProvider } from './confirm/ConfirmProvider';
import App from './App';

function mockSession(findings) {
  useSession.mockReturnValue({
    summary: { components: [], knowledge_bases: [] }, findings,
    transcript: [{ role: 'agent', text: 'ready' }], proposal: null,
    canUndo: false, canRedo: false, loading: false, sending: false,
    sessions: [], activeSessionId: null, usage: null, botName: null,
    upload: vi.fn(), startBlank: vi.fn(), loadSample: vi.fn(), send: vi.fn(), apply: vi.fn(), reject: vi.fn(),
    undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
    newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
    startNew: vi.fn(), renameBot: vi.fn(), editNodeText: vi.fn(),
  });
}
beforeEach(() => { vi.clearAllMocks(); api.getConfig.mockResolvedValue({ key_set: true }); api.getModels.mockResolvedValue({ models: [], custom_id: '' }); api.listSamples.mockResolvedValue([]); });
const renderApp = () => render(<ConfirmProvider><App /></ConfirmProvider>);

describe('App export gate', () => {
  it('exports directly when there are no errors', async () => {
    mockSession([{ severity: 'warning' }]);
    const open = vi.spyOn(window, 'open').mockImplementation(() => {});
    renderApp();
    fireEvent.click(screen.getByText('Export'));
    await waitFor(() => expect(open).toHaveBeenCalled());
    expect(screen.queryByTestId('confirm-dialog')).toBeNull();
    open.mockRestore();
  });

  it('shows the confirm dialog on errors and aborts on cancel', async () => {
    mockSession([{ severity: 'error' }, { severity: 'error' }]);
    const open = vi.spyOn(window, 'open').mockImplementation(() => {});
    renderApp();
    fireEvent.click(screen.getByText('Export'));
    fireEvent.click(await screen.findByTestId('confirm-cancel'));
    await waitFor(() => expect(screen.queryByTestId('confirm-dialog')).toBeNull());
    expect(open).not.toHaveBeenCalled();
    open.mockRestore();
  });

  it('proceeds on confirm', async () => {
    mockSession([{ severity: 'error' }]);
    const open = vi.spyOn(window, 'open').mockImplementation(() => {});
    renderApp();
    fireEvent.click(screen.getByText('Export'));
    fireEvent.click(await screen.findByTestId('confirm-ok'));
    await waitFor(() => expect(open).toHaveBeenCalled());
    open.mockRestore();
  });
});
