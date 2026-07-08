const EDGE_COLOR = {
  intent: 'var(--c-edge-intent)', condition: 'var(--c-edge-condition)',
  default: 'var(--c-edge-default)', next: 'var(--c-edge-next)', exit: 'var(--c-edge-exit)',
};
const XCOMP_COLOR = 'var(--c-edge-xcomp)';

export function buildGraph(summary) {
  const nodes = [];
  const edges = [];
  const kbBadges = {};
  if (!summary) return { nodes, edges, kbBadges };

  const kbTitleMap = {};
  for (const kb of summary.knowledge_bases || []) kbTitleMap[kb.knowledge_id] = kb.title;

  // Lookups for cross-component jump resolution.
  const componentEntry = {};
  const componentName = {};
  for (const comp of summary.components || []) {
    componentEntry[comp.uuid] = comp.entry_uuid || (comp.root_uuids && comp.root_uuids[0]) || null;
    componentName[comp.uuid] = comp.name;
  }

  const emittedKbNodes = new Set();

  for (const comp of summary.components || []) {
    const compNodes = Object.values(comp.nodes || {});
    nodes.push({
      id: comp.uuid, type: 'componentNode', position: { x: 0, y: 0 },
      data: { label: comp.name, nodeCount: compNodes.length, kind: 'component' },
    });
    for (const node of compNodes) {
      // If this node jumps to another component, hint the target in its label.
      const gotoBranch = (node.branches || []).find((b) => b.target_component);
      const nodeLabel = gotoBranch
        ? `${node.label} → ${componentName[gotoBranch.target_component] || 'component'}`
        : node.label;
      nodes.push({
        id: node.uuid, type: 'flow', parentId: comp.uuid, extent: 'parent', position: { x: 0, y: 0 },
        data: { ...node, label: nodeLabel, tags: node.tags || [] },
      });
      if (node.allowed_kbs?.length) kbBadges[node.uuid] = node.allowed_kbs;
      for (let i = 0; i < (node.branches || []).length; i++) {
        const b = node.branches[i];
        if (b.target_uuid) {
          edges.push({
            id: `e-${node.uuid}-${b.target_uuid}-${b.kind}-${i}`, source: node.uuid, target: b.target_uuid,
            label: b.label || undefined, type: 'smoothstep', style: { stroke: EDGE_COLOR[b.kind] || 'var(--c-edge-default)' },
            data: { sourceComp: comp.uuid, sourceNode: node.uuid, targetComp: comp.uuid, targetNode: b.target_uuid },
          });
        } else if (b.target_component) {
          const entryUuid = componentEntry[b.target_component];
          const tgt = entryUuid || b.target_component;     // entry node, else box fallback
          const tname = componentName[b.target_component] || 'component';
          edges.push({
            id: `e-${node.uuid}-xcomp-${b.target_component}-${b.kind}-${i}`,
            source: node.uuid, target: tgt,
            label: `→ ${tname}`, type: 'smoothstep',
            style: { stroke: XCOMP_COLOR, strokeWidth: 2, strokeDasharray: '4 2' },
            markerEnd: { type: 'arrowclosed', color: XCOMP_COLOR },
            data: { sourceComp: comp.uuid, sourceNode: node.uuid, targetComp: b.target_component, targetNode: tgt },
          });
        } else if (b.target_kb != null) {
          const kbNodeId = `kb-${b.target_kb}`;
          if (!emittedKbNodes.has(kbNodeId)) {
            emittedKbNodes.add(kbNodeId);
            const title = kbTitleMap[b.target_kb] || String(b.target_kb);
            nodes.push({
              id: kbNodeId, position: { x: 0, y: 0 }, data: { label: `KB: ${title}`, kbNode: true, knowledge_id: b.target_kb },
              style: { background: 'var(--c-kb-bg)', border: '2px solid var(--c-kb-border)', borderRadius: 8, padding: 8, fontSize: 12 },
            });
          }
          edges.push({
            id: `e-${node.uuid}-kb-${b.target_kb}-${b.kind}-${i}`, source: node.uuid, target: kbNodeId,
            label: b.label || 'go to KB', type: 'smoothstep', style: { stroke: EDGE_COLOR.exit, strokeDasharray: '4 2' },
            data: { sourceComp: comp.uuid, sourceNode: node.uuid, targetComp: null, targetNode: kbNodeId },
          });
        } else if (b.terminal) {
          const tid = `term-${node.uuid}-${b.terminal}-${i}`;
          nodes.push({
            id: tid, parentId: comp.uuid, extent: 'parent', position: { x: 0, y: 0 },
            data: { terminal: b.terminal, label: b.terminal === 'hangup' ? 'Hang up' : 'Transfer' },
          });
          edges.push({
            id: `e-${node.uuid}-${tid}-${b.kind}-${i}`, source: node.uuid, target: tid, type: 'smoothstep',
            style: { stroke: EDGE_COLOR.exit },
            data: { sourceComp: comp.uuid, sourceNode: node.uuid, targetComp: comp.uuid, targetNode: tid },
          });
        }
      }
    }
  }
  return { nodes, edges, kbBadges };
}
