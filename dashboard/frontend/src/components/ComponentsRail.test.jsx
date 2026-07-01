import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ComponentsRail from './ComponentsRail';

const summary = { components: [
  { uuid: 'a', name: 'Greeting', nodes: { n1: { node_type: 'talk' }, n2: { node_type: 'exit' } } },
  { uuid: 'b', name: 'Router', nodes: { n3: { node_type: 'conditional' } } },
] };

describe('ComponentsRail filters', () => {
  it('builds chips from present node types and filters', () => {
    render(<ComponentsRail summary={summary} selectedComponentId={null} onSelectComponent={vi.fn()} />);
    expect(screen.getByTestId('chip-conditional')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('chip-conditional'));
    // only Router has a conditional node
    expect(screen.getByText('Router')).toBeInTheDocument();
    expect(screen.queryByText('Greeting')).toBeNull();
  });
  it('searches by component name', () => {
    render(<ComponentsRail summary={summary} selectedComponentId={null} onSelectComponent={vi.fn()} />);
    fireEvent.change(screen.getByTestId('component-search'), { target: { value: 'greet' } });
    expect(screen.getByText('Greeting')).toBeInTheDocument();
    expect(screen.queryByText('Router')).toBeNull();
  });
});
