import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
import FlowCanvas from './FlowCanvas';

describe('FlowCanvas empty state', () => {
  it('shows a hint when there are no components', () => {
    render(<FlowCanvas summary={{ components: [], knowledge_bases: [] }} onSelectNode={() => {}} />);
    expect(screen.getByText(/no components yet/i)).toBeInTheDocument();
  });
  it('does not show the hint when components exist', () => {
    render(<FlowCanvas summary={{ components: [
      { uuid: 'cA', name: 'A', entry_uuid: 'a1', root_uuids: ['a1'],
        nodes: { a1: { uuid: 'a1', label: 'N', node_type: 'talk', branches: [] } } },
    ], knowledge_bases: [] }} onSelectNode={() => {}} />);
    expect(screen.queryByText(/no components yet/i)).not.toBeInTheDocument();
  });
});
