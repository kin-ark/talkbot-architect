import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RightDock from './RightDock';

// jsdom lacks ResizeObserver (ReactFlow in SimulatorPanel does not mount one, but guard anyway)
globalThis.ResizeObserver = globalThis.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };

const talk = (uuid, text, branches) => ({ uuid, label: uuid, node_type: 'talk', text, branches, data: {} });
const br = (label, target_uuid) => ({ label, kind: 'intent', target_uuid, target_component: null, target_kb: null, terminal: null });
const summary = { components: [{
  uuid: 'c1', name: 'Main', sort_index: 0, entry_uuid: 't1', root_uuids: ['t1'], parent_uuid: '0',
  nodes: { t1: talk('t1', 'Hi', [br('Positive', 't1')]) },
}], knowledge_bases: [], tags: [] };

const baseChat = { transcript: [], proposal: null, sending: false, onSend: () => {}, onRetry: () => {},
  onApply: () => {}, onReject: () => {}, onCancel: () => {}, canUndo: false, canRedo: false, onUndo: () => {}, onRedo: () => {} };

describe('RightDock Simulate tab', () => {
  it('shows a Simulate tab that renders the setup form', () => {
    render(<RightDock activeTab="simulate" onTabChange={() => {}} summary={summary} findings={[]}
      chat={baseChat} intents={[]} onSimNode={() => {}} />);
    expect(screen.getByText('Simulate')).toBeInTheDocument();
    expect(screen.getByTestId('sim-setup')).toBeInTheDocument();
  });

  it('reports the current node to onSimNode after Start', () => {
    const onSimNode = vi.fn();
    render(<RightDock activeTab="simulate" onTabChange={() => {}} summary={summary} findings={[]}
      chat={baseChat} intents={[]} onSimNode={onSimNode} />);
    fireEvent.click(screen.getByTestId('sim-start'));
    expect(onSimNode).toHaveBeenCalledWith('t1');
  });
});
