import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
import FlowCanvas from './FlowCanvas';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'A', entry_uuid: 'a1', root_uuids: ['a1'], nodes: {
    a1: { uuid: 'a1', label: 'Added', node_type: 'talk', branches: [] },
    a2: { uuid: 'a2', label: 'Changed', node_type: 'talk', branches: [] },
  } } ], knowledge_bases: [] };

describe('FlowCanvas highlight', () => {
  it('rings added and changed nodes when highlight is set + components expanded', () => {
    const { container } = render(
      <FlowCanvas summary={SUMMARY} onSelectNode={() => {}} focusComponentId="cA"
        highlight={{ added_nodes: ['a1'], changed_nodes: ['a2'] }} />);
    // expanded via focusComponentId → inner nodes render with ring boxShadow
    const html = container.innerHTML;
    expect(html).toContain('var(--c-success)');
    expect(html).toContain('var(--c-warning)');
  });
  it('no rings without highlight', () => {
    const { container } = render(
      <FlowCanvas summary={SUMMARY} onSelectNode={() => {}} focusComponentId="cA" />);
    expect(container.innerHTML).not.toContain('var(--c-success)');
  });
});
