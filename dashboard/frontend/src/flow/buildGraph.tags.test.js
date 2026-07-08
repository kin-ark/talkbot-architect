import { describe, it, expect } from 'vitest';
import { buildGraph } from './buildGraph';

const SUMMARY_WITH_TAGS = {
  components: [
    {
      uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
      nodes: {
        a1: {
          uuid: 'a1', label: 'Greet', node_type: 'talk',
          tags: [
            { category: 'disposition', value: 'positive' },
            { category: 'feedback', value: 'helpful' },
          ],
          branches: [],
        },
        a2: {
          uuid: 'a2', label: 'Exit', node_type: 'exit',
          tags: [],
          branches: [],
        },
      },
    },
  ],
  knowledge_bases: [],
};

const SUMMARY_WITHOUT_TAGS = {
  components: [
    {
      uuid: 'cA', name: 'Greeting', entry_uuid: 'a1',
      nodes: {
        a1: { uuid: 'a1', label: 'Greet', node_type: 'talk', branches: [] },
      },
    },
  ],
  knowledge_bases: [],
};

describe('buildGraph tags support', () => {
  it('includes tags in node data when present', () => {
    const { nodes } = buildGraph(SUMMARY_WITH_TAGS);
    const greetNode = nodes.find((n) => n.id === 'a1');
    expect(greetNode).toBeTruthy();
    expect(greetNode.data.tags).toEqual([
      { category: 'disposition', value: 'positive' },
      { category: 'feedback', value: 'helpful' },
    ]);
  });

  it('includes empty tags array for nodes without tags', () => {
    const { nodes } = buildGraph(SUMMARY_WITHOUT_TAGS);
    const greetNode = nodes.find((n) => n.id === 'a1');
    expect(greetNode).toBeTruthy();
    expect(greetNode.data.tags).toEqual([]);
  });

  it('includes empty tags array when tags undefined', () => {
    const { nodes } = buildGraph(SUMMARY_WITH_TAGS);
    const exitNode = nodes.find((n) => n.id === 'a2');
    expect(exitNode).toBeTruthy();
    expect(exitNode.data.tags).toEqual([]);
  });
});
