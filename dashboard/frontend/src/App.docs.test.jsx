import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import * as api from './api';
import { useSession } from './state/useSession';
import App from './App';

const HOOKS = {
  summary: null, findings: [], transcript: [], proposal: null,
  canUndo: false, canRedo: false, loading: false, sending: false,
  sessions: [], activeSessionId: null, usage: null, botName: null,
  upload: vi.fn(), startBlank: vi.fn(), loadSample: vi.fn(), send: vi.fn(), apply: vi.fn(),
  reject: vi.fn(), undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(), startNew: vi.fn(),
  newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
  renameBot: vi.fn(), editNodeText: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getConfig.mockResolvedValue({ key_set: true });
  api.getModels.mockResolvedValue({ models: [], custom_id: '' });
  api.listSamples.mockResolvedValue([]);
  useSession.mockReturnValue(HOOKS);
});

describe('App documentation page', () => {
  it('opens the full-screen DocsPage (not the overlay) from the rail', () => {
    render(<App />);
    fireEvent.click(screen.getByTestId('rail-docs'));
    expect(screen.getByTestId('docs-page')).toBeInTheDocument();
    expect(screen.queryByTestId('page-overlay')).toBeNull();
  });

  it('Back from DocsPage returns to the workspace', () => {
    render(<App />);
    fireEvent.click(screen.getByTestId('rail-docs'));
    fireEvent.click(screen.getByTestId('docs-back'));
    expect(screen.queryByTestId('docs-page')).toBeNull();
    expect(screen.getByTestId('session-rail')).toBeInTheDocument();
  });

  it('Settings still uses the overlay', () => {
    render(<App />);
    fireEvent.click(screen.getByTestId('rail-settings'));
    expect(screen.getByTestId('page-overlay')).toBeInTheDocument();
    expect(screen.queryByTestId('docs-page')).toBeNull();
  });
});
