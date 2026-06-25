import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
import FlowCanvas from './FlowCanvas';
import ComponentsRail from './ComponentsRail';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'Greeting', entry_uuid: 'a1', root_uuids: ['a1'],
    nodes: { a1: { uuid: 'a1', label: 'GreetNode', node_type: 'talk', branches: [] } } },
], knowledge_bases: [] };

describe('Plan-B controls are typed buttons', () => {
  it('FlowCanvas toolbar buttons have type=button', () => {
    render(<FlowCanvas summary={SUMMARY} onSelectNode={() => {}} />);
    for (const name of ['Map', 'Detail', 'Fit']) {
      expect(screen.getByRole('button', { name }).getAttribute('type')).toBe('button');
    }
  });
  it('ComponentsRail rows have type=button', () => {
    render(<ComponentsRail summary={SUMMARY} onSelectComponent={() => {}} />);
    expect(screen.getByRole('button', { name: /greeting/i }).getAttribute('type')).toBe('button');
  });
});
