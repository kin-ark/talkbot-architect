import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/react';

beforeEach(() => {
  global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
});

import FlowCanvas from './FlowCanvas';

// Two components with a cross-component goto from A -> B.
const SUMMARY = {
  components: [
    { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'],
      nodes: { a1: { uuid: 'a1', label: 'Greet', node_type: 'talk',
                     branches: [{ kind: 'exit', target_component: 'cB' }] } } },
    { uuid: 'cB', name: 'Payment', entry_uuid: 'b1', root_uuids: ['b1'],
      nodes: { b1: { uuid: 'b1', label: 'Ask', node_type: 'talk', branches: [] } } },
  ],
  knowledge_bases: [],
};

describe('FlowCanvas component-box handles', () => {
  it('renders connection handles on the collapsed component boxes', () => {
    // Default render = all collapsed. Component boxes must carry ReactFlow
    // handles, otherwise cross-component edges have no anchor and never draw.
    const { container } = render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    const handles = container.querySelectorAll('.react-flow__handle');
    // 2 component boxes × (1 source + 1 target) = at least 4, children hidden.
    expect(handles.length).toBeGreaterThanOrEqual(4);
  });
});
