import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FlowCanvas from './FlowCanvas';
import { buildGraph } from '../flow/buildGraph';

// ResizeObserver polyfill is already in setupTests.js.

const SUMMARY = {
  components: [
    {
      uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'],
      nodes: {
        a1: {
          uuid: 'a1', label: 'Greet', node_type: 'talk',
          branches: [{ kind: 'exit', target_component: 'cB' }],
        },
      },
    },
    {
      uuid: 'cB', name: 'Payment', entry_uuid: 'b1', root_uuids: ['b1'],
      nodes: {
        b1: { uuid: 'b1', label: 'AskNode', node_type: 'talk', branches: [] },
      },
    },
  ],
  knowledge_bases: [],
};

// ---------------------------------------------------------------------------
// Derived-edge harness: mirrors the reroute logic in FlowCanvas so we can
// assert target without relying on xyflow rendering edge labels in jsdom.
// ---------------------------------------------------------------------------
function rerouteEdges(summary, expanded) {
  const { nodes, edges } = buildGraph(summary);
  const visibleIds = new Set(nodes.map((n) => n.id));
  const seen = new Set();
  const rerouted = [];
  for (const e of edges) {
    const sComp = e.data?.sourceComp;
    const tComp = e.data?.targetComp;
    const source = sComp && !expanded.has(sComp) ? sComp : e.source;
    const target = tComp && !expanded.has(tComp) ? tComp : e.target;
    if (!visibleIds.has(source) || !visibleIds.has(target)) continue;
    const key = `${source}->${target}`;
    if (source === target) continue;
    if ((!expanded.has(sComp) || !expanded.has(tComp)) && seen.has(key)) continue;
    seen.add(key);
    rerouted.push({ ...e, source, target });
  }
  return rerouted;
}

describe('FlowCanvas cross-component connections', () => {
  it('renders both component boxes on load (collapsed)', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    expect(screen.getByText('Greeting')).toBeInTheDocument();
    expect(screen.getByText('Payment')).toBeInTheDocument();
  });

  it('cross-component edge lands on the box (cB) when target is collapsed', () => {
    const rerouted = rerouteEdges(SUMMARY, new Set()); // nothing expanded
    const xedge = rerouted.find((e) => e.data?.targetComp === 'cB');
    expect(xedge).toBeTruthy();
    // target component collapsed → reroute to box id
    expect(xedge.target).toBe('cB');
    // style/marker survive reroute
    expect(xedge.style.stroke).toBe('var(--c-edge-xcomp)');
    expect(xedge.markerEnd).toBeTruthy();
    expect(xedge.label).toBe('→ Payment');
  });

  it('cross-component edge lands on the entry node (b1) when target is expanded', () => {
    const rerouted = rerouteEdges(SUMMARY, new Set(['cB'])); // cB expanded
    const xedge = rerouted.find((e) => e.data?.targetComp === 'cB');
    expect(xedge).toBeTruthy();
    // target expanded → stay on the entry node emitted by buildGraph
    expect(xedge.target).toBe('b1'); // cB.entry_uuid
    // style/marker survive reroute
    expect(xedge.style.stroke).toBe('var(--c-edge-xcomp)');
    expect(xedge.markerEnd).toBeTruthy();
    expect(xedge.label).toBe('→ Payment');
  });

  it('renders inner nodes after expanding both components', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    fireEvent.click(screen.getByText('Greeting'));
    fireEvent.click(screen.getByText('Payment'));
    expect(screen.getByText('AskNode')).toBeInTheDocument();
  });
});
