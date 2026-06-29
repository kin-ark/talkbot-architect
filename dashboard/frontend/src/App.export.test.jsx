import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import { useSession } from './state/useSession';
import App from './App';

function mockSession(findings) {
  useSession.mockReturnValue({
    summary: { components: [], knowledge_bases: [] }, findings,
    transcript: [{ role: 'agent', text: 'ready' }], proposal: null,
    canUndo: false, canRedo: false, loading: false, sending: false,
    sessions: [], activeSessionId: null, usage: null, botName: null,
    upload: vi.fn(), startBlank: vi.fn(), send: vi.fn(), apply: vi.fn(), reject: vi.fn(),
    undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
    newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
    startNew: vi.fn(), renameBot: vi.fn(), editNodeText: vi.fn(),
  });
}

beforeEach(() => { vi.clearAllMocks(); });

describe('App export gate', () => {
  it('exports directly when there are no errors', () => {
    mockSession([{ severity: 'warning' }]);
    const open = vi.spyOn(window, 'open').mockImplementation(() => {});
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<App />);
    fireEvent.click(screen.getByText('Export'));
    expect(confirm).not.toHaveBeenCalled();
    expect(open).toHaveBeenCalled();
    open.mockRestore(); confirm.mockRestore();
  });

  it('warns on errors and aborts on cancel', () => {
    mockSession([{ severity: 'error' }, { severity: 'error' }]);
    const open = vi.spyOn(window, 'open').mockImplementation(() => {});
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<App />);
    fireEvent.click(screen.getByText('Export'));
    expect(confirm).toHaveBeenCalled();
    expect(open).not.toHaveBeenCalled();
    open.mockRestore(); confirm.mockRestore();
  });

  it('warns on errors and proceeds on confirm', () => {
    mockSession([{ severity: 'error' }]);
    const open = vi.spyOn(window, 'open').mockImplementation(() => {});
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<App />);
    fireEvent.click(screen.getByText('Export'));
    expect(confirm).toHaveBeenCalled();
    expect(open).toHaveBeenCalled();
    open.mockRestore(); confirm.mockRestore();
  });
});
