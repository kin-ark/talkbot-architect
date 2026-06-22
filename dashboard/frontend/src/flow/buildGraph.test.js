import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';

const summary = {
  components: [{
    uuid: 'c1', name: '1. Greeting', root_uuids: ['n1'],
    nodes: {
      n1: { uuid: 'n1', label: 'Greet', node_type: 'talk', text: 'Hi', referenced_vars: [], allowed_kbs: [],
            branches: [{ label: 'Positive', kind: 'intent', target_uuid: 'n2' }] },
      n2: { uuid: 'n2', label: 'Bye', node_type: 'exit', text: '', referenced_vars: [], allowed_kbs: [],
            branches: [{ label: 'hang up', kind: 'exit', terminal: 'hangup' }] },
    },
  }],
  knowledge_bases: [],
};

describe('buildGraph', () => {
  it('creates a node per flow node and a labeled branch edge', () => {
    const { nodes, edges } = buildGraph(summary);
    expect(nodes.find((n) => n.id === 'n1')).toBeTruthy();
    const e = edges.find((x) => x.source === 'n1' && x.target === 'n2');
    expect(e.label).toBe('Positive');
  });
  it('emits a terminal node for hangup exit', () => {
    const { nodes } = buildGraph(summary);
    expect(nodes.some((n) => n.data?.terminal === 'hangup')).toBe(true);
  });
});
