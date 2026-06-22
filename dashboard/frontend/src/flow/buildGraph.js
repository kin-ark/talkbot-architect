const EDGE_COLOR = { intent: '#f59e0b', condition: '#8b5cf6', default: '#94a3b8', next: '#cbd5e1', exit: '#0ea5e9' };

export function buildGraph(summary) {
  const nodes = [];
  const edges = [];
  if (!summary) return { nodes, edges };
  for (const comp of summary.components || []) {
    nodes.push({ id: comp.uuid, type: 'group', position: { x: 0, y: 0 },
      data: { label: comp.name, kind: 'component' },
      style: { padding: 8, border: '2px dashed #cbd5e1', borderRadius: 12, background: '#f8fafc' } });
    for (const node of Object.values(comp.nodes || {})) {
      nodes.push({ id: node.uuid, parentNode: comp.uuid, position: { x: 0, y: 0 },
        data: { ...node, label: node.label } });
      for (const b of node.branches || []) {
        if (b.target_uuid) {
          edges.push({ id: `e-${node.uuid}-${b.target_uuid}-${b.label}`, source: node.uuid,
            target: b.target_uuid, label: b.label || undefined, type: 'smoothstep',
            style: { stroke: EDGE_COLOR[b.kind] || '#cbd5e1' } });
        } else if (b.terminal) {
          const tid = `term-${node.uuid}-${b.terminal}`;
          nodes.push({ id: tid, parentNode: comp.uuid, position: { x: 0, y: 0 },
            data: { terminal: b.terminal, label: b.terminal === 'hangup' ? '☎ Hang up' : '→ Transfer' } });
          edges.push({ id: `e-${node.uuid}-${tid}`, source: node.uuid, target: tid, type: 'smoothstep',
            style: { stroke: EDGE_COLOR.exit } });
        }
      }
    }
  }
  return { nodes, edges };
}
