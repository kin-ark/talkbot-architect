import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import IntentsPanel from './IntentsPanel';

const INTENTS = [
  { id: '1', name: 'Charge Confirmation', type: 'user', keyword_count: 4, response_count: 3, needs_nlu: false },
  { id: '2', name: 'IOS Enter', type: 'system', keyword_count: 0, response_count: 0, needs_nlu: false },
  { id: '3', name: 'Blank User', type: 'user', keyword_count: 0, response_count: 0, needs_nlu: true },
];

describe('IntentsPanel', () => {
  it('lists intents with type badge and counts', () => {
    render(<IntentsPanel intents={INTENTS} />);
    expect(screen.getAllByTestId('intent-row')).toHaveLength(3);
    const row = screen.getByText('Charge Confirmation').closest('[data-testid="intent-row"]');
    expect(row.textContent).toMatch(/User/);
    expect(row.textContent).toMatch(/4 keywords/);
    expect(row.textContent).toMatch(/3 responses/);
  });
  it('flags needs-NLU intents', () => {
    render(<IntentsPanel intents={INTENTS} />);
    const row = screen.getByText('Blank User').closest('[data-testid="intent-row"]');
    expect(row.textContent).toMatch(/no NLU signal/i);
  });
  it('filters by type', () => {
    render(<IntentsPanel intents={INTENTS} />);
    fireEvent.click(screen.getByTestId('chip-system'));
    expect(screen.getAllByTestId('intent-row')).toHaveLength(1);
    expect(screen.getByText('IOS Enter')).toBeInTheDocument();
  });
  it('filters needs-nlu', () => {
    render(<IntentsPanel intents={INTENTS} />);
    fireEvent.click(screen.getByTestId('chip-needs-nlu'));
    expect(screen.getAllByTestId('intent-row')).toHaveLength(1);
    expect(screen.getByText('Blank User')).toBeInTheDocument();
  });
  it('searches by name', () => {
    render(<IntentsPanel intents={INTENTS} />);
    fireEvent.change(screen.getByTestId('intent-search'), { target: { value: 'charge' } });
    expect(screen.getAllByTestId('intent-row')).toHaveLength(1);
  });
  it('shows empty states', () => {
    const { rerender } = render(<IntentsPanel intents={[]} />);
    expect(screen.getByText(/No intents yet/i)).toBeInTheDocument();
    rerender(<IntentsPanel intents={INTENTS} />);
    fireEvent.change(screen.getByTestId('intent-search'), { target: { value: 'zzz' } });
    expect(screen.getByText(/No intents match/i)).toBeInTheDocument();
  });
});
