import { useMemo, useState, useCallback, useEffect } from 'react';
import { ReactFlow, Background, Controls, MiniMap, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { buildGraph } from '../flow/buildGraph';
import { layoutComponents } from '../flow/componentLayout';

const TYPE_COLOR = {
  talk: '#3b82f6', conditional: '#8b5cf6', variable_assignment: '#10b981',
  exit: '#0ea5e9', llm: '#f59e0b', unknown: '#94a3b8',
  nested_component: '#f97316', exit_port: '#14b8a6',
};

function ComponentNode({ data }) {
  return (
    <div
      role="button"
      onClick={data.onToggle}
      data-testid={`comp-${data.label}`}
      style={{ width: '100%', height: '100%', border: '2px dashed var(--c-border)',
               borderRadius: 12, background: 'var(--c-surface)', cursor: 'pointer' }}
    >
      {/* Invisible anchors so ReactFlow can draw cross-component edges to/from a
          collapsed component box. Without handles no edge path is computed.
          opacity:0 (not display:none, which would also drop the edge endpoint). */}
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px',
                    fontSize: 13, fontWeight: 600, color: 'var(--c-text)' }}>
        <span>{data.expanded ? '▾' : '▸'}</span>
        <span>{data.label}</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 400, color: 'var(--c-text-2)' }}>
          {data.nodeCount} node{data.nodeCount === 1 ? '' : 's'}
        </span>
      </div>
    </div>
  );
}

const nodeTypes = { componentNode: ComponentNode };

export default function FlowCanvas({ summary, onSelectNode, focusComponentId, highlight }) {
  const [expanded, setExpanded] = useState(() => new Set());
  const [rf, setRf] = useState(null);
  const [hoverId, setHoverId] = useState(null);

  // Reset to all-collapsed whenever a new summary loads.
  const summaryKey = summary ? JSON.stringify(summary.components?.map((c) => c.uuid)) : '';
  // eslint-disable-next-line react-hooks/set-state-in-effect -- legitimate summary-change reset; collapsed state is derived from which summary is loaded
  useEffect(() => { setExpanded(new Set()); }, [summaryKey]);

  // Rail-driven focus: expand the chosen component and fit to it.
  useEffect(() => {
    if (!focusComponentId) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- prop-driven focus expansion; rf.fitView() must run after the expand re-render so the node has layout
    setExpanded((prev) => new Set(prev).add(focusComponentId));
    if (rf) rf.fitView({ nodes: [{ id: focusComponentId }], duration: 300, padding: 0.3 });
  }, [focusComponentId, rf]);

  const toggle = useCallback((id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const { nodes, edges, compIds } = useMemo(() => {
    if (!summary) return { nodes: [], edges: [], compIds: [] };
    const { nodes: rawNodes, edges: rawEdges } = buildGraph(summary);
    const positioned = layoutComponents(rawNodes, rawEdges, expanded);

    // Style + wire nodes; drop hidden (collapsed) children from render.
    const visible = positioned
      .filter((n) => !n.hidden)
      .map((n) => {
        if (n.data?.kind === 'component') {
          return { ...n, data: { ...n.data, expanded: expanded.has(n.id), onToggle: () => toggle(n.id) } };
        }
        if (n.data?.kbNode || n.data?.terminal) return n;
        const added = highlight?.added_nodes?.includes(n.id);
        const changed = highlight?.changed_nodes?.includes(n.id);
        const ring = added ? '0 0 0 2px var(--c-success)'
          : changed ? '0 0 0 2px var(--c-warning)' : undefined;
        return {
          ...n,
          style: {
            ...n.style, background: 'var(--c-surface)', border: '1px solid var(--c-border)',
            borderLeft: `4px solid ${TYPE_COLOR[n.data?.node_type] || '#94a3b8'}`,
            borderRadius: 8, padding: 8, fontSize: 12, width: 200, color: 'var(--c-text)',
            ...(ring ? { boxShadow: ring } : {}),
          },
          data: { ...n.data },
        };
      });

    // Reroute edges: an endpoint whose component is collapsed lands on the box.
    const visibleIds = new Set(visible.map((n) => n.id));
    const seen = new Set();
    const rerouted = [];
    for (const e of rawEdges) {
      const sComp = e.data?.sourceComp;
      const tComp = e.data?.targetComp;
      const source = sComp && !expanded.has(sComp) ? sComp : e.source;
      const target = tComp && !expanded.has(tComp) ? tComp : e.target;
      if (!visibleIds.has(source) || !visibleIds.has(target)) continue;
      const key = `${source}->${target}`;
      if (source === target) continue;           // self-loop after collapse — skip
      if ((!expanded.has(sComp) || !expanded.has(tComp)) && seen.has(key)) continue; // aggregate box edges
      seen.add(key);
      // pointerEvents:none + interactionWidth:0 so an edge never steals hover
      // from a node it touches (was causing enter/leave flicker on highlight).
      rerouted.push({ ...e, source, target, interactionWidth: 0,
        style: { ...e.style, pointerEvents: 'none' } });
    }
    return { nodes: visible, edges: rerouted, compIds: (summary?.components || []).map((c) => c.uuid) };
  }, [summary, expanded, toggle, highlight]);

  const showMap = () => setExpanded(new Set());
  const showDetail = () => setExpanded(new Set(compIds));
  const fit = () => rf?.fitView({ duration: 300, padding: 0.2 });
  const mode = expanded.size === 0 ? 'map' : expanded.size === compIds.length ? 'detail' : null;

  // Hover a node → light up its edges, fade the rest, so a tangle of overlapping
  // lines becomes one readable path. Edges only: the `nodes` array is passed
  // through referentially unchanged so the node layer never re-renders on hover
  // (re-rendering it repaints under the cursor and bounces mouseenter/leave =
  // flicker). Guarded so a stale hoverId (node hidden by collapse) is a no-op.
  const displayEdges = useMemo(() => {
    if (!hoverId || !nodes.some((n) => n.id === hoverId)) return edges;
    return edges.map((e) => (e.source === hoverId || e.target === hoverId)
      ? { ...e, animated: true, style: { ...e.style, strokeWidth: 3, opacity: 1 } }
      : { ...e, style: { ...e.style, opacity: 0.1 } });
  }, [nodes, edges, hoverId]);

  return (
    <div className="w-full h-full flex flex-col" data-testid="flow-canvas">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-divider bg-surface">
        <div className="inline-flex rounded-md border border-border overflow-hidden text-sm">
          <button type="button" onClick={showMap}
            className={`px-3 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${mode === 'map' ? 'bg-primary text-primary-fg' : 'text-text-secondary hover:bg-surface-muted'}`}>Map</button>
          <button type="button" onClick={showDetail}
            className={`px-3 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${mode === 'detail' ? 'bg-primary text-primary-fg' : 'text-text-secondary hover:bg-surface-muted'}`}>Detail</button>
        </div>
        <button type="button" onClick={fit}
          className="px-3 py-1 text-sm rounded-md border border-border text-text-secondary hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">Fit</button>
        <span className="ml-auto text-xs text-text-tertiary">{compIds.length} components</span>
      </div>
      <div className="flex-1 min-h-0 relative">
        {compIds.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
            <p className="text-sm text-text-tertiary">No components yet — describe a bot in Chat.</p>
          </div>
        )}
        <ReactFlow
          nodes={nodes}
          edges={displayEdges}
          nodeTypes={nodeTypes}
          onInit={setRf}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.05}
          onNodeMouseEnter={(_, n) => setHoverId(n.id)}
          onNodeMouseLeave={() => setHoverId(null)}
          onNodeClick={(_, n) => { if (n.data?.kind !== 'component') onSelectNode?.(n.data); }}
        >
          <Background gap={16} color="var(--c-border)" />
          <Controls />
          <MiniMap pannable zoomable />
        </ReactFlow>
      </div>
    </div>
  );
}
