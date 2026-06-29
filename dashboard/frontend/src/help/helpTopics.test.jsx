import { describe, it, expect } from 'vitest';
import { helpTopics } from './helpTopics';

describe('helpTopics', () => {
  it('still has the 11 topics with stable ids', () => {
    expect(helpTopics).toHaveLength(11);
    expect(helpTopics[0].id).toBe('getting-started');
  });

  it('every topic has an icon component', () => {
    for (const t of helpTopics) {
      expect(t.icon, `topic ${t.id} missing icon`).toBeTruthy();
    }
  });

  it('embeds the five figure sentinels in the right topics', () => {
    const byId = Object.fromEntries(helpTopics.map((t) => [t.id, t.body]));
    expect(byId['getting-started']).toContain('@@fig:layout@@');
    expect(byId['node-types']).toContain('@@fig:node-types@@');
    expect(byId['agent']).toContain('@@fig:proposal-flow@@');
    expect(byId['findings']).toContain('@@fig:severity@@');
    expect(byId['knowledge-bases']).toContain('@@fig:kb-flow@@');
  });

  it('keeps the in-progress KB editing section', () => {
    const kb = helpTopics.find((t) => t.id === 'knowledge-bases');
    expect(kb.body).toMatch(/Editing a KB/);
    expect(kb.body).toMatch(/in progress/i);
  });
});
