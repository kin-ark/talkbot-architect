import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import * as api from './api';
import { useSession } from './state/useSession';
import { ConfirmProvider } from './confirm/ConfirmProvider';
import App from './App';

const DEFAULTS = {
  summary: { components: [], knowledge_bases: [] }, findings: [],
  transcript: [{ role: 'agent', text: 'ready' }], proposal: null,
  canUndo: false, canRedo: false, loading: false, sending: false,
  sessions: [], activeSessionId: null, usage: null, botName: null, intents: [],
  isComponent: false, componentWarnings: [], backendDown: false,
  upload: vi.fn(), startBlank: vi.fn(), loadSample: vi.fn(), send: vi.fn(), apply: vi.fn(),
  reject: vi.fn(), undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
  newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
  startNew: vi.fn(), renameBot: vi.fn(), editNodeText: vi.fn(),
};
const mockSession = (over) => useSession.mockReturnValue({ ...DEFAULTS, ...over });
beforeEach(() => {
  vi.clearAllMocks();
  api.getConfig.mockResolvedValue({ key_set: true });
  api.getModels.mockResolvedValue({ models: [], custom_id: '' });
});
const renderApp = () => render(<ConfirmProvider><App /></ConfirmProvider>);

describe('App UX', () => {
  it('shows a backend-down banner when the server is unreachable', () => {
    mockSession({ backendDown: true });
    renderApp();
    expect(screen.getByTestId('backend-down')).toBeInTheDocument();
  });

  it('no banner when the backend is reachable', () => {
    mockSession({ backendDown: false });
    renderApp();
    expect(screen.queryByTestId('backend-down')).toBeNull();
  });

  it('Ctrl+Z triggers undo', () => {
    const undo = vi.fn();
    mockSession({ canUndo: true, undo });
    renderApp();
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
    expect(undo).toHaveBeenCalled();
  });

  it('Ctrl+Shift+Z triggers redo', () => {
    const redo = vi.fn();
    mockSession({ canRedo: true, redo });
    renderApp();
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true, shiftKey: true });
    expect(redo).toHaveBeenCalled();
  });

  it('ignores the shortcut while typing in an input', () => {
    const undo = vi.fn();
    mockSession({ canUndo: true, undo });
    renderApp();
    const input = document.createElement('input');
    document.body.appendChild(input);
    fireEvent.keyDown(input, { key: 'z', ctrlKey: true });
    expect(undo).not.toHaveBeenCalled();
    input.remove();
  });
});
