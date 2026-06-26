import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
import { useSession } from './state/useSession';
import App from './App';

// Drive App into the loaded state by mocking useSession via a spy on the module.
vi.mock('./state/useSession');

const SUMMARY = { components: [{ uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'],
  nodes: { a1: { uuid: 'a1', label: 'GreetNode', node_type: 'talk', branches: [] } } }], knowledge_bases: [] };

beforeEach(() => {
  useSession.mockReturnValue({
    summary: SUMMARY, findings: [], transcript: [{ role: 'agent', text: 'ready' }],
    proposal: null, canUndo: false, canRedo: false, loading: false, sending: false,
    sessions: [], activeSessionId: null, usage: null,
    upload: vi.fn(), startBlank: vi.fn(), send: vi.fn(), apply: vi.fn(), reject: vi.fn(),
    undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
    newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
  });
});

describe('App three-pane workspace', () => {
  it('renders session rail + graph + dock when a session is loaded', () => {
    render(<App />);
    expect(screen.getByTestId('session-rail')).toBeInTheDocument();
    expect(screen.getByTestId('flow-canvas')).toBeInTheDocument();
    expect(screen.getByTestId('right-dock')).toBeInTheDocument();
    // component outline now lives behind the dock Components tab
    fireEvent.click(screen.getByText('Components'));
    expect(screen.getByTestId('components-rail')).toBeInTheDocument();
  });
  it('dock defaults to Chat', () => {
    render(<App />);
    expect(screen.getByText('ready')).toBeInTheDocument();   // chat transcript visible
  });
});
