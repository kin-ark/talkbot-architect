import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
vi.mock('./state/useSession');
import { useSession } from './state/useSession';
import App from './App';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'],
    nodes: { a1: { uuid: 'a1', label: 'GreetNode', node_type: 'talk', branches: [] } } },
], knowledge_bases: [] };
const FINDINGS = [{ code: 'WIZ102', severity: 'error', message: 'orphan node', id: 'a1' }];

beforeEach(() => {
  useSession.mockReturnValue({
    summary: SUMMARY, findings: FINDINGS, transcript: [{ role: 'agent', text: 'ready' }],
    proposal: null, canUndo: false, canRedo: false, loading: false, sending: false,
    sessions: [], activeSessionId: null, usage: null,
    upload: vi.fn(), startBlank: vi.fn(), send: vi.fn(), apply: vi.fn(), reject: vi.fn(),
    undo: vi.fn(), redo: vi.fn(), cancel: vi.fn(), reset: vi.fn(),
    newSession: vi.fn(), switchSession: vi.fn(), renameSession: vi.fn(), deleteSession: vi.fn(),
    startNew: vi.fn(),
  });
});

describe('App selection wiring', () => {
  it('clicking a finding opens Properties and focuses its owning component', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Findings'));          // dock → Findings tab
    fireEvent.click(screen.getByText(/orphan node/));        // finding row → select node a1
    // Properties tab now active: NodePropertiesPanel renders the node label/id.
    expect(screen.getByTestId('right-dock').textContent).toMatch(/GreetNode|a1/);
    // Owning component cA is now the focused/active row in the dock Components tab.
    fireEvent.click(screen.getByText('Components'));
    const railRow = screen.getByTestId('components-rail').querySelector('.text-primary.font-semibold');
    expect(railRow).not.toBeNull();
    expect(railRow.textContent).toMatch(/Greeting/);
  });
});
