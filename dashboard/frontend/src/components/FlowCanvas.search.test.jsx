import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
import FlowCanvas from './FlowCanvas';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'], nodes: {
    a1: { uuid: 'a1', label: 'AskName', node_type: 'talk', branches: [] },
    a2: { uuid: 'a2', label: 'Goodbye', node_type: 'talk', branches: [] },
  } },
], knowledge_bases: [] };

describe('FlowCanvas node search', () => {
  it('typing a query rings matching nodes + expands the owner + shows a count', () => {
    const { container } = render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    fireEvent.change(screen.getByTestId('node-search'), { target: { value: 'askname' } });
    // owner component expanded → the matched node renders
    expect(screen.getByText('AskName')).toBeInTheDocument();
    // a primary ring (boxShadow with --c-primary) is present in the rendered graph
    expect(container.innerHTML).toContain('var(--c-primary)');
    // match count shows 1
    expect(screen.getByTestId('search-count').textContent).toMatch(/1/);
  });

  it('empty query shows no count and no primary ring', () => {
    const { container } = render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} focusComponentId="cA" />);
    expect(screen.queryByTestId('search-count')).not.toBeInTheDocument();
    expect(container.innerHTML).not.toContain('var(--c-primary)');
  });
});
