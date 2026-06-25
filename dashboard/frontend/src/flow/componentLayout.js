import dagre from 'dagre';

const COLLAPSED_W = 240;
const COLLAPSED_H = 56;
const NODE_W = 200;
const NODE_H = 60;
const HEADER_H = 40;
const PAD = 16;

export function layoutComponents(nodes, edges, expanded) {
  const comps = nodes.filter((n) => n.data?.kind === 'component');
  const kbNodes = nodes.filter((n) => !n.parentId && n.data?.kind !== 'component');
  const childrenByComp = {};
  for (const n of nodes) if (n.parentId) (childrenByComp[n.parentId] ||= []).push(n);

  const sizeByComp = {};
  const positionedChildren = [];

  for (const comp of comps) {
    const kids = childrenByComp[comp.id] || [];
    if (expanded.has(comp.id) && kids.length) {
      const g = new dagre.graphlib.Graph();
      g.setDefaultEdgeLabel(() => ({}));
      g.setGraph({ rankdir: 'TB', nodesep: 48, ranksep: 72 });
      kids.forEach((k) => g.setNode(k.id, { width: NODE_W, height: NODE_H }));
      edges.forEach((e) => {
        if (e.data?.sourceComp === comp.id && e.data?.targetComp === comp.id) {
          g.setEdge(e.data.sourceNode, e.data.targetNode);
        }
      });
      dagre.layout(g);
      let maxX = 0;
      let maxY = 0;
      kids.forEach((k) => {
        const p = g.node(k.id);
        const x = p.x - NODE_W / 2 + PAD;
        const y = p.y - NODE_H / 2 + HEADER_H + PAD;
        positionedChildren.push({ ...k, position: { x, y }, hidden: false });
        maxX = Math.max(maxX, x + NODE_W);
        maxY = Math.max(maxY, y + NODE_H);
      });
      sizeByComp[comp.id] = { width: Math.max(COLLAPSED_W, maxX + PAD), height: maxY + PAD };
    } else {
      kids.forEach((k) => positionedChildren.push({ ...k, hidden: true }));
      sizeByComp[comp.id] = { width: COLLAPSED_W, height: COLLAPSED_H };
    }
  }

  // Outer: arrange component boxes + top-level KB nodes via inter-component edges.
  const og = new dagre.graphlib.Graph();
  og.setDefaultEdgeLabel(() => ({}));
  og.setGraph({ rankdir: 'TB', nodesep: 100, ranksep: 130 });
  comps.forEach((c) => og.setNode(c.id, sizeByComp[c.id]));
  kbNodes.forEach((k) => og.setNode(k.id, { width: COLLAPSED_W, height: COLLAPSED_H }));
  const seen = new Set();
  edges.forEach((e) => {
    const s = e.data?.sourceComp;
    const t = e.data?.targetComp;
    if (s && t && s !== t) {
      const key = `${s}>${t}`;
      if (!seen.has(key)) { seen.add(key); og.setEdge(s, t); }
    } else if (s && t == null && typeof e.target === 'string' && e.target.startsWith('kb-')) {
      const key = `${s}>${e.target}`;
      if (!seen.has(key)) { seen.add(key); og.setEdge(s, e.target); }
    }
  });
  dagre.layout(og);

  const positionedComps = comps.map((c) => {
    const p = og.node(c.id);
    const sz = sizeByComp[c.id];
    return { ...c, position: { x: p.x - sz.width / 2, y: p.y - sz.height / 2 },
             style: { ...c.style, width: sz.width, height: sz.height } };
  });
  const positionedKb = kbNodes.map((k) => {
    const p = og.node(k.id);
    return { ...k, position: { x: p.x - COLLAPSED_W / 2, y: p.y - COLLAPSED_H / 2 } };
  });

  // Parent boxes first, then children, then KB (xyflow requires parents before children).
  return [...positionedComps, ...positionedChildren, ...positionedKb];
}
