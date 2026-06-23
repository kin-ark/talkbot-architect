import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

beforeEach(() => {
  global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
});

import FlowCanvas from './FlowCanvas';

const SUMMARY = {
  components: [
    { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
      nodes: { a1: { uuid: 'a1', label: 'GreetNode', node_type: 'talk', branches: [] } } },
    { uuid: 'cB', name: 'Payment', entry_uuid: 'b1',
      nodes: { b1: { uuid: 'b1', label: 'AskNode', node_type: 'talk', branches: [] } } },
  ],
  knowledge_bases: [],
};

describe('FlowCanvas component view', () => {
  it('renders a box per component, collapsed (child labels hidden) on load', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    expect(screen.getByText('Greeting')).toBeInTheDocument();
    expect(screen.getByText('Payment')).toBeInTheDocument();
    expect(screen.queryByText('GreetNode')).not.toBeInTheDocument();
  });

  it('expands a component when its header is clicked', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    fireEvent.click(screen.getByText('Greeting'));
    expect(screen.getByText('GreetNode')).toBeInTheDocument();
    // other component stays collapsed
    expect(screen.queryByText('AskNode')).not.toBeInTheDocument();
  });
});
