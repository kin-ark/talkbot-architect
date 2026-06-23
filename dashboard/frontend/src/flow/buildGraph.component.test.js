import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';

const SUMMARY = {
  components: [
    { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
      nodes: { a1: { uuid: 'a1', label: 'Greet', node_type: 'talk',
                     branches: [{ label: 'next', kind: 'next', target_uuid: 'a2' },
                                { label: 'go', kind: 'next', target_component: 'cB' }] },
               a2: { uuid: 'a2', label: 'Close', node_type: 'exit', branches: [] } } },
    { uuid: 'cB', name: 'Payment', entry_uuid: 'b1',
      nodes: { b1: { uuid: 'b1', label: 'Ask', node_type: 'talk', branches: [] } } },
  ],
  knowledge_bases: [],
};

describe('buildGraph component nesting', () => {
  it('emits componentNode boxes with nodeCount', () => {
    const { nodes } = buildGraph(SUMMARY);
    const comp = nodes.find((n) => n.id === 'cA');
    expect(comp.type).toBe('componentNode');
    expect(comp.data.kind).toBe('component');
    expect(comp.data.nodeCount).toBe(2);
  });

  it('children carry parentId + extent', () => {
    const { nodes } = buildGraph(SUMMARY);
    const child = nodes.find((n) => n.id === 'a1');
    expect(child.parentId).toBe('cA');
    expect(child.extent).toBe('parent');
  });

  it('edges carry endpoint component metadata', () => {
    const { edges } = buildGraph(SUMMARY);
    const intra = edges.find((e) => e.source === 'a1' && e.target === 'a2');
    expect(intra.data).toMatchObject({ sourceComp: 'cA', sourceNode: 'a1', targetComp: 'cA', targetNode: 'a2' });
    const cross = edges.find((e) => e.source === 'a1' && e.data?.targetComp === 'cB');
    expect(cross).toBeTruthy();
    expect(cross.data.sourceComp).toBe('cA');
  });

  it('parent nodes precede their children in the array', () => {
    const { nodes } = buildGraph(SUMMARY);
    expect(nodes.findIndex((n) => n.id === 'cA')).toBeLessThan(nodes.findIndex((n) => n.id === 'a1'));
  });
});
