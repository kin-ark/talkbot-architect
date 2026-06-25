import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ComponentsRail from './ComponentsRail';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'Greeting', nodes: { a: {}, b: {} } },
  { uuid: 'cB', name: 'Payment', nodes: { c: {} } },
] };

describe('ComponentsRail', () => {
  it('lists components with node counts', () => {
    render(<ComponentsRail summary={SUMMARY} onSelectComponent={() => {}} onAddComponent={() => {}} />);
    expect(screen.getByText('Greeting')).toBeInTheDocument();
    expect(screen.getByText('Payment')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();   // Greeting node count
  });

  it('selecting a component fires onSelectComponent with its uuid', () => {
    const onSelect = vi.fn();
    render(<ComponentsRail summary={SUMMARY} onSelectComponent={onSelect} onAddComponent={() => {}} />);
    fireEvent.click(screen.getByText('Payment'));
    expect(onSelect).toHaveBeenCalledWith('cB');
  });

  it('Add component fires onAddComponent', () => {
    const onAdd = vi.fn();
    render(<ComponentsRail summary={SUMMARY} onSelectComponent={() => {}} onAddComponent={onAdd} />);
    fireEvent.click(screen.getByText(/add component/i));
    expect(onAdd).toHaveBeenCalled();
  });
});
