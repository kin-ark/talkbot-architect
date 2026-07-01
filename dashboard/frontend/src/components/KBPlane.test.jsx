import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import KBPlane from './KBPlane';

const KBS = [
  { knowledge_id: 1, title: 'FAQ', intents: [1, 2], trigger_type: 'intent', is_user_created: true, multi_round: null },
  { knowledge_id: 2, title: 'System Monitor', intents: [], trigger_type: 'system', is_user_created: false, multi_round: null },
  { knowledge_id: 3, title: 'Booking', intents: [3], trigger_type: 'intent', is_user_created: true, multi_round: { components: [] } },
];

describe('KBPlane filters', () => {
  it('filters to system KBs', () => {
    render(<KBPlane knowledgeBases={KBS} onSelect={() => {}} />);
    fireEvent.click(screen.getByTestId('chip-system'));
    expect(screen.getAllByTestId('kb-row')).toHaveLength(1);
    expect(screen.getByText('System Monitor')).toBeInTheDocument();
  });
  it('filters to multi-round KBs', () => {
    render(<KBPlane knowledgeBases={KBS} onSelect={() => {}} />);
    fireEvent.click(screen.getByTestId('chip-multi-round'));
    expect(screen.getAllByTestId('kb-row')).toHaveLength(1);
    expect(screen.getByText('Booking')).toBeInTheDocument();
  });
  it('searches by title', () => {
    render(<KBPlane knowledgeBases={KBS} onSelect={() => {}} />);
    fireEvent.change(screen.getByTestId('kb-search'), { target: { value: 'faq' } });
    expect(screen.getAllByTestId('kb-row')).toHaveLength(1);
  });
});
