import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import * as api from './api';
import { useSession } from './state/useSession';
import App from './App';

const baseHook = {
  summary: null, findings: [], transcript: [{ role: 'agent', text: 'earlier chat' }],
  proposal: null, canUndo: false, canRedo: false, loading: false, sending: false,
  sessions: [{ id: 's1', name: 'Consultative Caring' }], activeSessionId: 's1', usage: null,
  botName: null, intents: [], isComponent: false, componentWarnings: [],
  upload: vi.fn(), startBlank: vi.fn(), loadSample: vi.fn(), send: vi.fn(), retry: vi.fn(),
  apply: vi.fn(), reject: vi.fn(), undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
  newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
  renameBot: vi.fn(), editNodeText: vi.fn(), startNew: vi.fn(),
};

beforeEach(() => { api.listSamples.mockResolvedValue([]); });

describe('App doc-less session', () => {
  it('renders the chat dock + entry options for an active doc-less session', () => {
    useSession.mockReturnValue({ ...baseHook });
    render(<App />);
    expect(screen.getByTestId('right-dock')).toBeInTheDocument();
    expect(screen.getByTestId('upload-zone')).toBeInTheDocument();
  });
  it('renders no dock on the true landing (no active session)', () => {
    useSession.mockReturnValue({ ...baseHook, activeSessionId: null, transcript: [] });
    render(<App />);
    expect(screen.queryByTestId('right-dock')).not.toBeInTheDocument();
  });
});
