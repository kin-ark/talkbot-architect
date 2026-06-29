import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import * as api from './api';
import { useSession } from './state/useSession';
import App from './App';

const BASE_SESSION = { id: 's1', name: 'A', updated: 1, usage: {} };

const BASE_HOOKS = {
  summary: null, findings: [], transcript: [], proposal: null,
  canUndo: false, canRedo: false, loading: false, sending: false,
  activeSessionId: null, usage: null,
  upload: vi.fn(), startBlank: vi.fn(), loadSample: vi.fn(), send: vi.fn(), apply: vi.fn(), reject: vi.fn(),
  undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
  newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
  startNew: vi.fn(), botName: null, renameBot: vi.fn(), editNodeText: vi.fn(),
};

beforeEach(() => {
  api.getConfig.mockResolvedValue({ key_set: true });
  api.listSamples.mockResolvedValue([]);
});

describe('App landing screen — SessionRail visibility', () => {
  it('shows session-rail AND upload affordance when sessions exist and summary is null', () => {
    useSession.mockReturnValue({
      ...BASE_HOOKS,
      sessions: [BASE_SESSION],
      activeSessionId: null,
    });
    render(<App />);
    expect(screen.getByTestId('session-rail')).toBeInTheDocument();
    expect(screen.getByTestId('upload-zone')).toBeInTheDocument();
    expect(screen.getByText(/Start from scratch/i)).toBeInTheDocument();
  });

  it('shows session-rail even when the sessions list is empty (unified shell)', () => {
    useSession.mockReturnValue({
      ...BASE_HOOKS,
      sessions: [],
      activeSessionId: null,
    });
    render(<App />);
    expect(screen.getByTestId('session-rail')).toBeInTheDocument();
    expect(screen.getByTestId('upload-zone')).toBeInTheDocument();
  });

  it('the rail New button calls startNew', () => {
    const startNew = vi.fn();
    useSession.mockReturnValue({ ...BASE_HOOKS, sessions: [], activeSessionId: null, startNew });
    render(<App />);
    fireEvent.click(screen.getByTestId('rail-new'));
    expect(startNew).toHaveBeenCalled();
  });
});
