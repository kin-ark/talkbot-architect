import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';

const SUMMARY = {
  components: [
    { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'],
      nodes: { a1: { uuid: 'a1', label: 'Greet', node_type: 'talk',
                     branches: [{ kind: 'exit', target_component: 'cB' }] } } },
    { uuid: 'cB', name: 'Payment', entry_uuid: 'b1', root_uuids: ['b1'],
      nodes: { b1: { uuid: 'b1', label: 'Ask', node_type: 'talk', branches: [] } } },
    { uuid: 'cC', name: 'NoEntry', entry_uuid: null, root_uuids: [],
      nodes: {} },
  ],
  knowledge_bases: [],
};

function xedge(summary) {
  return buildGraph(summary).edges.find((e) => e.data?.targetComp === 'cB');
}

describe('buildGraph cross-component connections', () => {
  it('targets the destination entry node, not the component id', () => {
    const e = xedge(SUMMARY);
    expect(e.target).toBe('b1');           // cB.entry_uuid
    expect(e.data.targetNode).toBe('b1');
    expect(e.data.targetComp).toBe('cB');
  });

  it('carries a distinct style + arrowhead + named label', () => {
    const e = xedge(SUMMARY);
    expect(e.markerEnd).toBeTruthy();
    expect(e.style.stroke).toBe('var(--c-edge-xcomp)');
    expect(e.label).toContain('Payment');
  });

  it('suffixes the goto node label with its target component', () => {
    const a1 = buildGraph(SUMMARY).nodes.find((n) => n.id === 'a1');
    expect(a1.data.label).toContain('Payment');
  });

  it('falls back to the component id when the target has no entry node', () => {
    const s = {
      ...SUMMARY,
      components: [
        { uuid: 'cX', name: 'Src', entry_uuid: 'x1', root_uuids: ['x1'],
          nodes: { x1: { uuid: 'x1', label: 'S', node_type: 'talk',
                         branches: [{ kind: 'exit', target_component: 'cC' }] } } },
        SUMMARY.components[2],   // cC has no entry
      ],
    };
    const e = buildGraph(s).edges.find((ed) => ed.data?.targetComp === 'cC');
    expect(e.target).toBe('cC');           // box fallback
  });
});
