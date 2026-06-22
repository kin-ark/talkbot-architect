const EDGE_COLOR = { intent: '#f59e0b', condition: '#8b5cf6', default: '#94a3b8', next: '#cbd5e1', exit: '#0ea5e9' };

export function buildGraph(summary) {
  const nodes = [];
  const edges = [];
  const kbBadges = {};
  if (!summary) return { nodes, edges, kbBadges };

  // Build lookup: component uuid → entry node uuid
  const componentEntry = {};
  for (const comp of summary.components || []) {
    const entryId = comp.entry_uuid || (comp.root_uuids && comp.root_uuids[0]);
    if (entryId) componentEntry[comp.uuid] = entryId;
  }

  // Build lookup: kb knowledge_id → title
  const kbTitleMap = {};
  for (const kb of summary.knowledge_bases || []) {
    kbTitleMap[kb.knowledge_id] = kb.title;
  }

  const emittedKbNodes = new Set();

  for (const comp of summary.components || []) {
    nodes.push({ id: comp.uuid, type: 'group', position: { x: 0, y: 0 },
      data: { label: comp.name, kind: 'component' },
      style: { padding: 8, border: '2px dashed #cbd5e1', borderRadius: 12, background: '#f8fafc' } });
    for (const node of Object.values(comp.nodes || {})) {
      nodes.push({ id: node.uuid, parentNode: comp.uuid, position: { x: 0, y: 0 },
        data: { ...node, label: node.label } });
      if (node.allowed_kbs?.length) kbBadges[node.uuid] = node.allowed_kbs;
      for (let i = 0; i < (node.branches || []).length; i++) {
        const b = node.branches[i];
        if (b.target_uuid) {
          edges.push({ id: `e-${node.uuid}-${b.target_uuid}-${b.kind}-${i}`, source: node.uuid,
            target: b.target_uuid, label: b.label || undefined, type: 'smoothstep',
            style: { stroke: EDGE_COLOR[b.kind] || '#cbd5e1' } });
        } else if (b.target_component) {
          // Retarget to destination component's entry node so the edge survives
          // FlowCanvas's group-node strip. Fall back to component uuid if no entry found.
          const resolvedTarget = componentEntry[b.target_component] || b.target_component;
          edges.push({
            id: `e-${node.uuid}-xcomp-${b.target_component}-${b.kind}-${i}`,
            source: node.uuid,
            target: resolvedTarget,
            label: b.label || 'go to component',
            type: 'smoothstep',
            style: { stroke: EDGE_COLOR.exit, strokeDasharray: '4 2' },
          });
        } else if (b.target_kb != null) {
          // Emit a synthetic KB node (once per distinct kb id) and an edge to it
          const kbNodeId = `kb-${b.target_kb}`;
          if (!emittedKbNodes.has(kbNodeId)) {
            emittedKbNodes.add(kbNodeId);
            const title = kbTitleMap[b.target_kb] || String(b.target_kb);
            nodes.push({
              id: kbNodeId,
              position: { x: 0, y: 0 },
              data: { label: `📖 KB ${title}`, kbNode: true },
              style: {
                background: '#fefce8',
                border: '2px solid #fbbf24',
                borderRadius: 8,
                padding: 8,
                fontSize: 12,
              },
            });
          }
          edges.push({
            id: `e-${node.uuid}-kb-${b.target_kb}-${b.kind}-${i}`,
            source: node.uuid,
            target: kbNodeId,
            label: b.label || 'go to KB',
            type: 'smoothstep',
            style: { stroke: EDGE_COLOR.exit, strokeDasharray: '4 2' },
          });
        } else if (b.terminal) {
          const tid = `term-${node.uuid}-${b.terminal}-${i}`;
          nodes.push({ id: tid, parentNode: comp.uuid, position: { x: 0, y: 0 },
            data: { terminal: b.terminal, label: b.terminal === 'hangup' ? '☎ Hang up' : '→ Transfer' } });
          edges.push({ id: `e-${node.uuid}-${tid}-${b.kind}-${i}`, source: node.uuid, target: tid, type: 'smoothstep',
            style: { stroke: EDGE_COLOR.exit } });
        }
      }
    }
  }
  return { nodes, edges, kbBadges };
}
