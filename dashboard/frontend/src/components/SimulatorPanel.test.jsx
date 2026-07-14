import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SimulatorPanel from './SimulatorPanel';

const talk = (uuid, text, branches) => ({ uuid, label: uuid, node_type: 'talk', text, branches, data: {} });
const exit = (uuid) => ({ uuid, label: uuid, node_type: 'exit', text: 'Bye', branches: [{ label: 'exit', kind: 'exit', terminal: 'hangup' }], data: {} });
const br = (label, target_uuid) => ({ label, kind: 'intent', target_uuid, target_component: null, target_kb: null, terminal: null });
const summary = { components: [{
  uuid: 'c1', name: 'Main', sort_index: 0, entry_uuid: 't1', root_uuids: ['t1'], parent_uuid: '0',
  nodes: { t1: talk('t1', 'Hello there', [br('Positive', 'e1')]), e1: exit('e1') },
}] };

describe('SimulatorPanel', () => {
  it('empty summary shows a hint', () => {
    render(<SimulatorPanel summary={{ components: [] }} />);
    expect(screen.getByTestId('sim-empty')).toBeInTheDocument();
  });

  it('start speaks the entry text and shows branch buttons', () => {
    render(<SimulatorPanel summary={summary} />);
    fireEvent.click(screen.getByTestId('sim-start'));
    expect(screen.getByText('Hello there')).toBeInTheDocument();
    expect(screen.getByText('Positive')).toBeInTheDocument();
  });

  it('choosing a branch advances to the ended banner and reports the node', () => {
    const onCurrentNode = vi.fn();
    render(<SimulatorPanel summary={summary} onCurrentNode={onCurrentNode} />);
    fireEvent.click(screen.getByTestId('sim-start'));
    expect(onCurrentNode).toHaveBeenCalledWith('t1');
    fireEvent.click(screen.getByText('Positive'));
    expect(screen.getByTestId('sim-ended')).toBeInTheDocument();
    expect(onCurrentNode).toHaveBeenLastCalledWith(null); // ended → cleared
  });

  it('restart returns to a fresh run', () => {
    render(<SimulatorPanel summary={summary} />);
    fireEvent.click(screen.getByTestId('sim-start'));
    fireEvent.click(screen.getByText('Positive'));
    fireEvent.click(screen.getByText('Restart'));
    expect(screen.getByText('Hello there')).toBeInTheDocument();
  });
});
