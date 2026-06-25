import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
import FlowCanvas from './FlowCanvas';

const SUMMARY = {
  components: [
    { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'],
      nodes: { a1: { uuid: 'a1', label: 'GreetNode', node_type: 'talk', branches: [] } } },
    { uuid: 'cB', name: 'Payment', entry_uuid: 'b1', root_uuids: ['b1'],
      nodes: { b1: { uuid: 'b1', label: 'AskNode', node_type: 'talk', branches: [] } } },
  ],
  knowledge_bases: [],
};

describe('FlowCanvas toolbar', () => {
  it('renders Map/Detail + Fit controls; collapsed by default (no inner labels)', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    expect(screen.getByText('Map')).toBeInTheDocument();
    expect(screen.getByText('Detail')).toBeInTheDocument();
    expect(screen.getByText('Fit')).toBeInTheDocument();
    expect(screen.queryByText('GreetNode')).not.toBeInTheDocument();
  });

  it('Detail expands all components; Map re-collapses', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    fireEvent.click(screen.getByText('Detail'));
    expect(screen.getByText('GreetNode')).toBeInTheDocument();
    expect(screen.getByText('AskNode')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Map'));
    expect(screen.queryByText('GreetNode')).not.toBeInTheDocument();
  });

  it('focusComponentId expands that component on mount', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} focusComponentId="cA" />);
    expect(screen.getByText('GreetNode')).toBeInTheDocument();   // cA expanded
    expect(screen.queryByText('AskNode')).not.toBeInTheDocument(); // cB still collapsed
  });
});
