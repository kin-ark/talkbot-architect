import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import FlowCanvas from './FlowCanvas';

// @xyflow/react uses ResizeObserver internally; jsdom doesn't include it.
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const summary = { components: [{ uuid: 'c1', name: 'A', root_uuids: ['n1'],
  nodes: { n1: { uuid: 'n1', label: 'Greet', node_type: 'talk', text: 'Hi', referenced_vars: [], allowed_kbs: [], branches: [] } } }],
  knowledge_bases: [] };

describe('FlowCanvas', () => {
  it('renders the canvas container', () => {
    render(<FlowCanvas summary={summary} onSelectNode={() => {}} />);
    expect(screen.getByTestId('flow-canvas')).toBeInTheDocument();
  });
});
