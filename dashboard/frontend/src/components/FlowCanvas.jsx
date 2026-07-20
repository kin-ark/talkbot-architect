import { useMemo, useState, useCallback, useEffect } from 'react';
import { ReactFlow, Background, Controls, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { buildGraph } from '../flow/buildGraph';
import { layoutComponents } from '../flow/componentLayout';
import { tagColor } from './ui/tagColor';

const TYPE_COLOR = {
  talk: 'var(--c-node-talk)', conditional: 'var(--c-node-conditional)',
  variable_assignment: 'var(--c-node-assign)', exit: 'var(--c-node-exit)',
  llm: 'var(--c-node-llm)', unknown: 'var(--c-node-unknown)',
  nested_component: 'var(--c-node-nested)', exit_port: 'var(--c-node-exit-port)',
};

const LEGEND_EDGES = [
  ['intent', 'var(--c-edge-intent)'], ['condition', 'var(--c-edge-condition)'],
  ['next', 'var(--c-edge-next)'], ['exit', 'var(--c-edge-exit)'],
  ['default', 'var(--c-edge-default)'], ['cross-component', 'var(--c-edge-xcomp)'],
];
const LEGEND_NODES = [
  ['talk', 'var(--c-node-talk)'], ['conditional', 'var(--c-node-conditional)'],
  ['assign', 'var(--c-node-assign)'], ['exit', 'var(--c-node-exit)'],
  ['llm', 'var(--c-node-llm)'], ['nested', 'var(--c-node-nested)'],
  ['exit_port', 'var(--c-node-exit-port)'], ['unknown', 'var(--c-node-unknown)'],
];

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

function FlowNode({ data }) {
  return (
    <div className="w-full h-full">
      <Handle type="target" position={Position.Top} />
      <div style={{ fontSize: 12 }}>{data.label}</div>
      {data.tags?.length > 0 && (
        <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {data.tags.slice(0, 3).map((t, i) => (
            <span key={i} data-testid="node-tag"
              className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] ${tagColor(t.category)}`}
              style={{ fontSize: 10 }}
              title={`${t.category}: ${t.value}`}>
              <span style={{ fontSize: 8 }}>●</span>{t.value}
            </span>
          ))}
          {data.tags.length > 3 && <span style={{ fontSize: 10 }}>+{data.tags.length - 3}</span>}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { componentNode: ComponentNode, flow: FlowNode };

export default function FlowCanvas({ summary, onSelectNode, focusComponentId, highlight, onSelectKb, simCurrentNode }) {
  const [expanded, setExpanded] = useState(() => new Set());
  const [rf, setRf] = useState(null);
  const [hoverId, setHoverId] = useState(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const [search, setSearch] = useState('');

  // Reset to all-collapsed whenever a new summary loads.
  const summaryKey = useMemo(
    () => (summary ? JSON.stringify(summary.components?.map((c) => c.uuid)) : ''),
    [summary]);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- legitimate summary-change reset; collapsed state is derived from which summary is loaded
  useEffect(() => { setExpanded(new Set()); }, [summaryKey]);

  // Rail-driven focus: expand the chosen component and fit to it.
  useEffect(() => {
    if (!focusComponentId) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- prop-driven focus expansion; rf.fitView() must run after the expand re-render so the node has layout
    setExpanded((prev) => new Set(prev).add(focusComponentId));
    if (rf) rf.fitView({ nodes: [{ id: focusComponentId }], duration: 300, padding: 0.3 });
  }, [focusComponentId, rf]);

  // Simulator: expand the current node's owner and pan to it.
  useEffect(() => {
    if (!simCurrentNode) return;
    let owner = null;
    for (const c of summary?.components || []) {
      if (c.nodes && c.nodes[simCurrentNode]) { owner = c.uuid; break; }
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- prop-driven sim focus; fitView after expand re-render
    if (owner) setExpanded((prev) => new Set(prev).add(owner));
    if (rf) rf.fitView({ nodes: [{ id: simCurrentNode }], duration: 300, padding: 0.4 });
  }, [simCurrentNode, rf, summary]);

  const toggle = useCallback((id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const { searchMatchIds, searchOwners } = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return { searchMatchIds: new Set(), searchOwners: new Set() };
    const ids = new Set(); const owners = new Set();
    for (const c of summary?.components || []) {
      for (const n of Object.values(c.nodes || {})) {
        if ((n.label || '').toLowerCase().includes(q)) { ids.add(n.uuid); owners.add(c.uuid); }
      }
    }
    return { searchMatchIds: ids, searchOwners: owners };
  }, [summary, search]);

  // Auto-expand owner components of search matches so matched nodes are visible.
  useEffect(() => {
    if (searchOwners.size === 0) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- search-driven expansion so matched children render
    setExpanded((prev) => { const next = new Set(prev); searchOwners.forEach((id) => next.add(id)); return next; });
  }, [searchOwners]);

  // Expensive geometry (buildGraph + two dagre passes) depends ONLY on the
  // graph shape (summary) and which components are expanded. Keep it in its own
  // memo so styling-only changes (search, simulator, preview highlight) don't
  // trigger a full relayout.
  const layout = useMemo(() => {
    if (!summary) return { positioned: [], rawEdges: [], compIds: [] };
    const { nodes: rawNodes, edges: rawEdges } = buildGraph(summary);
    const positioned = layoutComponents(rawNodes, rawEdges, expanded);
    return { positioned, rawEdges, compIds: (summary.components || []).map((c) => c.uuid) };
  }, [summary, expanded]);

  const { nodes, edges, compIds } = useMemo(() => {
    const { positioned, rawEdges } = layout;
    if (!summary) return { nodes: [], edges: [], compIds: [] };

    // Style + wire nodes; drop hidden (collapsed) children from render.
    const visible = positioned
      .filter((n) => !n.hidden)
      .map((n) => {
        if (n.data?.kind === 'component') {
          return { ...n, data: { ...n.data, expanded: expanded.has(n.id), onToggle: () => toggle(n.id) } };
        }
        if (n.data?.kbNode || n.data?.terminal) return n;
        const isMatch = searchMatchIds.has(n.id);
        const isSim = simCurrentNode === n.id;
        const added = highlight?.added_nodes?.includes(n.id);
        const changed = highlight?.changed_nodes?.includes(n.id);
        const ring = isSim ? '0 0 0 3px var(--c-primary)'
          : isMatch ? '0 0 0 2px var(--c-primary)'
          : added ? '0 0 0 2px var(--c-success)'
          : changed ? '0 0 0 2px var(--c-warning)' : undefined;
        return {
          ...n,
          style: {
            ...n.style, background: 'var(--c-surface)', border: '1px solid var(--c-border)',
            borderLeft: `4px solid ${TYPE_COLOR[n.data?.node_type] || 'var(--c-node-unknown)'}`,
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
    return { nodes: visible, edges: rerouted, compIds: layout.compIds };
  }, [layout, summary, expanded, toggle, highlight, searchMatchIds, simCurrentNode]);

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
        <button type="button" onClick={() => setLegendOpen((v) => !v)} data-testid="legend-toggle"
          className={`px-3 py-1 text-sm rounded-md border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${legendOpen ? 'bg-primary text-primary-fg' : 'text-text-secondary hover:bg-surface-muted'}`}>Legend</button>
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search nodes…"
          data-testid="node-search"
          className="ml-2 w-40 border border-border rounded-md px-2 py-1 text-xs bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary" />
        {search.trim() && (
          <span data-testid="search-count" className="text-xs text-text-tertiary">{searchMatchIds.size} match{searchMatchIds.size === 1 ? '' : 'es'}</span>
        )}
        <span className="ml-auto text-xs text-text-tertiary">{compIds.length} components</span>
      </div>
      <div className="flex-1 min-h-0 relative">
        {compIds.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
            <p className="text-sm text-text-tertiary">No components yet — describe a bot in Chat.</p>
          </div>
        )}
        {legendOpen && (
          <div data-testid="graph-legend"
            className="absolute top-2 right-2 z-20 rounded-lg border border-border bg-surface shadow-card p-3 text-xs space-y-2 max-w-[14rem]">
            <div>
              <div className="font-semibold text-text-secondary mb-1">Edges</div>
              {LEGEND_EDGES.map(([label, color]) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="inline-block w-4 h-0.5 rounded" style={{ background: color }} />
                  <span className="text-text">{label}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="font-semibold text-text-secondary mb-1">Node types</div>
              {LEGEND_NODES.map(([label, color]) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-sm" style={{ background: color }} />
                  <span className="text-text">{label}</span>
                </div>
              ))}
            </div>
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
          onNodeClick={(_, n) => {
            if (n.data?.kbNode) onSelectKb?.(n.data.knowledge_id);
            else if (n.data?.kind !== 'component') onSelectNode?.(n.data);
          }}
        >
          <Background gap={16} color="var(--c-border)" />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
