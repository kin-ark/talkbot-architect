import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
import FlowCanvas from './FlowCanvas';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'A', entry_uuid: 'a1', root_uuids: ['a1'],
    nodes: { a1: { uuid: 'a1', label: 'N1', node_type: 'talk', branches: [] } } },
], knowledge_bases: [] };

describe('FlowCanvas legend', () => {
  it('legend is hidden until toggled, then lists edge + node kinds', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    expect(screen.queryByTestId('graph-legend')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('legend-toggle'));
    const legend = screen.getByTestId('graph-legend');
    expect(legend).toBeInTheDocument();
    expect(legend.textContent).toMatch(/intent/i);          // an edge kind
    expect(legend.textContent).toMatch(/cross-component/i);  // xcomp
    expect(legend.textContent).toMatch(/talk/i);            // a node type
    expect(legend.textContent).toMatch(/conditional/i);
  });
});
