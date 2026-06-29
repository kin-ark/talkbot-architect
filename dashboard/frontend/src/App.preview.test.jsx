import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import { useSession } from './state/useSession';
import App from './App';

const PROPOSAL = {
  diff: '+x', checker_delta: null, change_summary: 'Adds 1 component',
  proposed_summary: { components: [{ uuid: 'cP', name: 'Proposed', entry_uuid: 'p1', root_uuids: ['p1'],
    nodes: { p1: { uuid: 'p1', label: 'NewNode', node_type: 'talk', branches: [] } } }], knowledge_bases: [] },
  change_set: { added_components: ['cP'], added_nodes: ['p1'], changed_nodes: [], removed_nodes: [], removed_components: [] },
};

beforeEach(() => {
  useSession.mockReturnValue({
    summary: { components: [], knowledge_bases: [] }, findings: [],
    transcript: [{ role: 'agent', text: 'ready' }], proposal: PROPOSAL,
    canUndo: false, canRedo: false, loading: false, sending: false,
    sessions: [], activeSessionId: null, usage: null,
    upload: vi.fn(), startBlank: vi.fn(), send: vi.fn(), apply: vi.fn(), reject: vi.fn(),
    undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
    newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
    startNew: vi.fn(),
  });
});

describe('App graph preview', () => {
  it('clicking Preview in graph shows the preview banner', () => {
    render(<App />);
    fireEvent.click(screen.getByText(/preview in graph/i));
    expect(screen.getByText(/previewing proposed change/i)).toBeInTheDocument();
  });
  it('Exit preview clears the banner', () => {
    render(<App />);
    fireEvent.click(screen.getByText(/preview in graph/i));
    fireEvent.click(screen.getByText(/exit preview/i));
    expect(screen.queryByText(/previewing proposed change/i)).not.toBeInTheDocument();
  });
});
