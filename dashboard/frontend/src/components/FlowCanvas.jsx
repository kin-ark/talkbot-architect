import React, { useMemo } from 'react';
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { buildGraph } from '../flow/buildGraph';

const TYPE_COLOR = {
  talk: '#3b82f6',
  conditional: '#8b5cf6',
  variable_assignment: '#10b981',
  exit: '#0ea5e9',
  llm: '#f59e0b',
  unknown: '#94a3b8',
};

function layout(nodes, edges) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 80 });
  nodes.forEach((n) => g.setNode(n.id, { width: 220, height: 70 }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const p = g.node(n.id);
    return p ? { ...n, position: { x: p.x - 110, y: p.y - 35 } } : n;
  });
}

export default function FlowCanvas({ summary, onSelectNode }) {
  const { nodes, edges } = useMemo(() => {
    const { nodes: rawNodes, edges: rawEdges } = buildGraph(summary);

    // Strip group (component) nodes — xyflow v12 uses parentId not parentNode,
    // and dagre assigns absolute positions so nesting causes position bugs.
    // We render dialogue nodes only; component grouping is visual-only.
    const dialogueNodes = rawNodes
      .filter((n) => n.data?.kind !== 'component')
      .map(({ parentNode: _parentNode, extent: _extent, ...n }) => ({
        ...n,
        style: {
          ...n.style,
          borderLeft: `4px solid ${TYPE_COLOR[n.data?.node_type] || '#94a3b8'}`,
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 8,
          padding: 8,
          fontSize: 12,
          width: 220,
        },
        data: {
          ...n.data,
          label: `${n.data?.label || ''}${n.data?.node_type ? ` · ${n.data.node_type}` : ''}`,
        },
      }));

    // Only keep edges whose source and target both exist in dialogueNodes
    const nodeIds = new Set(dialogueNodes.map((n) => n.id));
    const filteredEdges = rawEdges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    return { nodes: layout(dialogueNodes, filteredEdges), edges: filteredEdges };
  }, [summary]);

  return (
    <div className="w-full h-full" data-testid="flow-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        minZoom={0.05}
        onNodeClick={(_, n) => onSelectNode?.(n.data)}
      >
        <Background gap={16} color="#e2e8f0" />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}
