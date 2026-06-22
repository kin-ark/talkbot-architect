import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';

// Component c2 now has an entry_uuid so we can assert edge retargeting.
const summary = {
  components: [
    {
      uuid: 'c1', name: 'A', entry_uuid: 'n1', root_uuids: ['n1'],
      nodes: {
        n1: {
          uuid: 'n1', label: 'go', node_type: 'goto_component', text: '', referenced_vars: [], allowed_kbs: [3],
          branches: [{ label: 'go to component', kind: 'exit', target_component: 'c2' }],
        },
      },
    },
    {
      uuid: 'c2', name: 'B', entry_uuid: 'n2-entry', root_uuids: ['n2-entry'],
      nodes: {
        'n2-entry': {
          uuid: 'n2-entry', label: 'Entry', node_type: 'talk', text: 'Hi', referenced_vars: [], allowed_kbs: [],
          branches: [],
        },
      },
    },
  ],
  knowledge_bases: [{ knowledge_id: 3, title: 'Price', kd_type: 0, intents: [] }],
};

// Separate fixture for KB jump test
const kbSummary = {
  components: [
    {
      uuid: 'c1', name: 'A', entry_uuid: 'n1', root_uuids: ['n1'],
      nodes: {
        n1: {
          uuid: 'n1', label: 'kb-jumper', node_type: 'goto_kb', text: '', referenced_vars: [], allowed_kbs: [],
          branches: [{ label: 'go to KB', kind: 'exit', target_kb: 183805 }],
        },
      },
    },
  ],
  knowledge_bases: [{ knowledge_id: 183805, title: 'Pricing FAQ', kd_type: 0, intents: [] }],
};

describe('buildGraph cross-component', () => {
  it('retargets cross-component edge to destination entry node (not component id)', () => {
    const { edges } = buildGraph(summary);
    // Edge must land on n2-entry, NOT c2
    expect(edges.some((e) => e.source === 'n1' && e.target === 'n2-entry')).toBe(true);
    expect(edges.some((e) => e.target === 'c2')).toBe(false);
  });

  it('cross-component edge has dashed exit style', () => {
    const { edges } = buildGraph(summary);
    const e = edges.find((x) => x.source === 'n1' && x.target === 'n2-entry');
    expect(e.style.strokeDasharray).toBeTruthy();
  });

  it('reports KB badges per node', () => {
    const { kbBadges } = buildGraph(summary);
    expect(kbBadges.n1).toEqual([3]);
  });
});

describe('buildGraph KB jump (target_kb)', () => {
  it('emits a synthetic kb- node for a target_kb branch', () => {
    const { nodes } = buildGraph(kbSummary);
    const kbNode = nodes.find((n) => n.id === 'kb-183805');
    expect(kbNode).toBeTruthy();
    expect(kbNode.data.kbNode).toBe(true);
    expect(kbNode.data.label).toContain('Pricing FAQ');
  });

  it('emits an edge from the source node to the kb- node', () => {
    const { edges } = buildGraph(kbSummary);
    expect(edges.some((e) => e.source === 'n1' && e.target === 'kb-183805')).toBe(true);
  });

  it('deduplicates synthetic KB nodes when multiple branches target the same KB', () => {
    const dupe = {
      components: [{
        uuid: 'c1', name: 'A', entry_uuid: 'na', root_uuids: ['na'],
        nodes: {
          na: {
            uuid: 'na', label: 'x', node_type: 'talk', text: '', referenced_vars: [], allowed_kbs: [],
            branches: [
              { label: 'go to KB', kind: 'exit', target_kb: 9 },
              { label: 'go to KB', kind: 'exit', target_kb: 9 },
            ],
          },
        },
      }],
      knowledge_bases: [{ knowledge_id: 9, title: 'FAQ', kd_type: 0, intents: [] }],
    };
    const { nodes } = buildGraph(dupe);
    expect(nodes.filter((n) => n.id === 'kb-9').length).toBe(1);
  });
});
