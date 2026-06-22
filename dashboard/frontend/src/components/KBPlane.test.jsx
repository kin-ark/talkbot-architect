import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import KBPlane from './KBPlane';

describe('KBPlane', () => {
  it('marks multi-round KBs and drills in', () => {
    const onDrillIn = vi.fn();
    render(<KBPlane knowledgeBases={[{ knowledge_id: 3, title: 'Price', kd_type: 0, intents: [],
      multi_round: { components: [], knowledge_bases: [] } }]} onDrillIn={onDrillIn} />);
    expect(screen.getByText(/multi-round/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Price/));
    expect(onDrillIn).toHaveBeenCalled();
  });
});
