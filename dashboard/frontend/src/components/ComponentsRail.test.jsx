import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ComponentsRail from './ComponentsRail';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'Greeting', nodes: { a: {}, b: {} } },
  { uuid: 'cB', name: 'Payment', nodes: { c: {} } },
] };

describe('ComponentsRail', () => {
  it('lists components with node counts', () => {
    render(<ComponentsRail summary={SUMMARY} onSelectComponent={() => {}} />);
    expect(screen.getByText('Greeting')).toBeInTheDocument();
    expect(screen.getByText('Payment')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();   // Greeting node count
  });

  it('selecting a component fires onSelectComponent with its uuid', () => {
    const onSelect = vi.fn();
    render(<ComponentsRail summary={SUMMARY} onSelectComponent={onSelect} />);
    fireEvent.click(screen.getByText('Payment'));
    expect(onSelect).toHaveBeenCalledWith('cB');
  });

  it('marks the selected component active', () => {
    render(<ComponentsRail summary={SUMMARY} selectedComponentId="cB"
      onSelectComponent={() => {}} />);
    const active = screen.getByRole('button', { name: /payment/i });
    expect(active.className).toContain('text-primary');
    expect(active.className).toContain('font-semibold');
  });
});
