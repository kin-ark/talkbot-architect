import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';

const SUMMARY = {
  knowledge_bases: [{ knowledge_id: 7, title: 'FAQ' }],
  components: [
    { uuid: 'cA', name: 'A', entry_uuid: 'a1', root_uuids: ['a1'], nodes: {
      a1: { uuid: 'a1', label: 'N1', node_type: 'talk', branches: [
        { kind: 'intent', label: 'yes', target_uuid: 'a2' },          // intra-component
        { kind: 'next', target_component: 'cB' },                     // cross-component
        { kind: 'next', target_kb: 7 },                               // KB jump
      ] },
      a2: { uuid: 'a2', label: 'N2', node_type: 'talk', branches: [] },
    } },
    { uuid: 'cB', name: 'B', entry_uuid: 'b1', root_uuids: ['b1'], nodes: {
      b1: { uuid: 'b1', label: 'M1', node_type: 'talk', branches: [] } } },
  ],
};

describe('buildGraph color tokens', () => {
  const { nodes, edges } = buildGraph(SUMMARY);
  it('intra-component edge uses an edge CSS var', () => {
    const e = edges.find((x) => x.target === 'a2');
    expect(e.style.stroke).toBe('var(--c-edge-intent)');
  });
  it('cross-component edge uses the xcomp CSS var', () => {
    const e = edges.find((x) => x.id.includes('xcomp'));
    expect(e.style.stroke).toBe('var(--c-edge-xcomp)');
    expect(e.markerEnd.color).toBe('var(--c-edge-xcomp)');
  });
  it('KB node uses KB CSS vars', () => {
    const kb = nodes.find((n) => n.data?.kbNode);
    expect(kb.style.background).toBe('var(--c-kb-bg)');
    expect(kb.style.border).toContain('var(--c-kb-border)');
  });
});
