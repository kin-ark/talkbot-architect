import { useMemo, useState, useCallback, useEffect } from 'react';
import { ReactFlow, Background, Controls, MiniMap, Handle, Position } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { buildGraph } from '../flow/buildGraph';
import { layoutComponents } from '../flow/componentLayout';

const TYPE_COLOR = {
  talk: '#3b82f6', conditional: '#8b5cf6', variable_assignment: '#10b981',
  exit: '#0ea5e9', llm: '#f59e0b', unknown: '#94a3b8',
};

function ComponentNode({ data }) {
  return (
    <div
      role="button"
      onClick={data.onToggle}
      data-testid={`comp-${data.label}`}
      style={{ width: '100%', height: '100%', border: '2px dashed #cbd5e1',
               borderRadius: 12, background: '#f8fafc', cursor: 'pointer' }}
    >
      {/* Invisible anchors so ReactFlow can draw cross-component edges to/from a
          collapsed component box. Without handles no edge path is computed.
          opacity:0 (not display:none, which would also drop the edge endpoint). */}
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px',
                    fontSize: 13, fontWeight: 600, color: '#334155' }}>
        <span>{data.expanded ? '▾' : '▸'}</span>
        <span>{data.label}</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 400, color: '#64748b' }}>
          {data.nodeCount} node{data.nodeCount === 1 ? '' : 's'}
        </span>
      </div>
    </div>
  );
}

const nodeTypes = { componentNode: ComponentNode };

export default function FlowCanvas({ summary, onSelectNode }) {
  const [expanded, setExpanded] = useState(() => new Set());

  // Reset to all-collapsed whenever a new summary loads.
  const summaryKey = summary ? JSON.stringify(summary.components?.map((c) => c.uuid)) : '';
  // eslint-disable-next-line react-hooks/set-state-in-effect -- legitimate summary-change reset; collapsed state is derived from which summary is loaded, not from a parent prop sync
  useEffect(() => { setExpanded(new Set()); }, [summaryKey]);

  const toggle = useCallback((id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const { nodes, edges } = useMemo(() => {
    if (!summary) return { nodes: [], edges: [] };
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
        return {
          ...n,
          style: {
            ...n.style, background: '#fff', border: '1px solid #e2e8f0',
            borderLeft: `4px solid ${TYPE_COLOR[n.data?.node_type] || '#94a3b8'}`,
            borderRadius: 8, padding: 8, fontSize: 12, width: 200,
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
      rerouted.push({ ...e, source, target });
    }
    return { nodes: visible, edges: rerouted };
  }, [summary, expanded, toggle]);

  return (
    <div className="w-full h-full" data-testid="flow-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.05}
        onNodeClick={(_, n) => { if (n.data?.kind !== 'component') onSelectNode?.(n.data); }}
      >
        <Background gap={16} color="#e2e8f0" />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}
