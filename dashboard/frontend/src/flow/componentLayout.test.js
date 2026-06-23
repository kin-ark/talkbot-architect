import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';
import { layoutComponents } from './componentLayout';

const SUMMARY = {
  components: [
    { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
      nodes: { a1: { uuid: 'a1', label: 'Greet', node_type: 'talk', branches: [{ kind: 'next', target_uuid: 'a2' }] },
               a2: { uuid: 'a2', label: 'Close', node_type: 'exit', branches: [] } } },
    { uuid: 'cB', name: 'Payment', entry_uuid: 'b1',
      nodes: { b1: { uuid: 'b1', label: 'Ask', node_type: 'talk', branches: [] } } },
  ],
  knowledge_bases: [],
};

function boxes(nodes) { return nodes.filter((n) => n.data?.kind === 'component'); }

describe('layoutComponents', () => {
  it('collapsed box is smaller than expanded box', () => {
    const { nodes, edges } = buildGraph(SUMMARY);
    const collapsed = layoutComponents(nodes, edges, new Set());
    const expanded = layoutComponents(nodes, edges, new Set(['cA']));
    const cCollapsed = boxes(collapsed).find((n) => n.id === 'cA');
    const cExpanded = boxes(expanded).find((n) => n.id === 'cA');
    expect(cExpanded.style.height).toBeGreaterThan(cCollapsed.style.height);
  });

  it('hides children of collapsed components, shows children of expanded', () => {
    const { nodes, edges } = buildGraph(SUMMARY);
    const out = layoutComponents(nodes, edges, new Set(['cA']));
    const a1 = out.find((n) => n.id === 'a1');   // in expanded cA
    const b1 = out.find((n) => n.id === 'b1');   // in collapsed cB
    expect(a1.hidden).toBeFalsy();
    expect(b1.hidden).toBe(true);
  });

  it('expanded children sit within the parent box bounds', () => {
    const { nodes, edges } = buildGraph(SUMMARY);
    const out = layoutComponents(nodes, edges, new Set(['cA']));
    const box = boxes(out).find((n) => n.id === 'cA');
    const a1 = out.find((n) => n.id === 'a1');    // position is relative to parent
    expect(a1.position.x).toBeGreaterThanOrEqual(0);
    expect(a1.position.y).toBeGreaterThanOrEqual(0);
    expect(a1.position.x).toBeLessThanOrEqual(box.style.width);
    expect(a1.position.y).toBeLessThanOrEqual(box.style.height);
  });

  it('component boxes do not overlap', () => {
    const { nodes, edges } = buildGraph(SUMMARY);
    const out = layoutComponents(nodes, edges, new Set());
    const [x, y] = boxes(out);
    const sep = Math.abs(x.position.x - y.position.x) + Math.abs(x.position.y - y.position.y);
    expect(sep).toBeGreaterThan(0);
  });

  it('returns parent boxes before their children', () => {
    const { nodes, edges } = buildGraph(SUMMARY);
    const out = layoutComponents(nodes, edges, new Set(['cA']));
    expect(out.findIndex((n) => n.id === 'cA')).toBeLessThan(out.findIndex((n) => n.id === 'a1'));
  });
});
