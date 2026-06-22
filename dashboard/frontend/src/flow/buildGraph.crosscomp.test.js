import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';

const summary = {
  components: [
    { uuid: 'c1', name: 'A', root_uuids: ['n1'], nodes: {
      n1: { uuid: 'n1', label: 'go', node_type: 'exit', text: '', referenced_vars: [], allowed_kbs: [3],
            branches: [{ label: 'go to component', kind: 'exit', target_component: 'c2' }] } } },
    { uuid: 'c2', name: 'B', root_uuids: [], nodes: {} },
  ],
  knowledge_bases: [{ knowledge_id: 3, title: 'Price', kd_type: 0, intents: [] }],
};

describe('buildGraph cross-component', () => {
  it('links exit node to the target component', () => {
    const { edges } = buildGraph(summary);
    expect(edges.some((e) => e.source === 'n1' && e.target === 'c2')).toBe(true);
  });
  it('reports KB badges per node', () => {
    const { kbBadges } = buildGraph(summary);
    expect(kbBadges.n1).toEqual([3]);
  });
});
