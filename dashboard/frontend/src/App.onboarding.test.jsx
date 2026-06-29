import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; localStorage.clear(); });
vi.mock('./api');
vi.mock('./state/useSession');
import * as api from './api';
import { useSession } from './state/useSession';
import App from './App';

function mockSession() {
  useSession.mockReturnValue({
    summary: null, findings: [], transcript: [], proposal: null,
    canUndo: false, canRedo: false, loading: false, sending: false,
    sessions: [], activeSessionId: null, usage: null, botName: null,
    upload: vi.fn(), startBlank: vi.fn(), loadSample: vi.fn(), send: vi.fn(), apply: vi.fn(),
    reject: vi.fn(), undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
    newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
    startNew: vi.fn(), renameBot: vi.fn(), editNodeText: vi.fn(),
  });
}

beforeEach(() => { vi.clearAllMocks(); mockSession(); api.listSamples.mockResolvedValue([]); });

describe('App onboarding key-nudge', () => {
  it('shows the key nudge when no key is set', async () => {
    api.getConfig.mockResolvedValue({ key_set: false, provider: 'anthropic' });
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('key-nudge')).toBeInTheDocument());
  });

  it('hides the key nudge when a key is set', async () => {
    api.getConfig.mockResolvedValue({ key_set: true, provider: 'anthropic' });
    render(<App />);
    await waitFor(() => expect(api.getConfig).toHaveBeenCalled());
    expect(screen.queryByTestId('key-nudge')).toBeNull();
  });
});
