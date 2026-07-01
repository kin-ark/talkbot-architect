import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import KBPlane from './KBPlane';

describe('KBPlane', () => {
  it('fires onSelect for any row (including simple KBs)', () => {
    const onSelect = vi.fn();
    const kbs = [
      { knowledge_id: 1, title: 'Simple', intents: [5], multi_round: null },
      { knowledge_id: 2, title: 'MR', intents: [], multi_round: { components: [] } },
    ];
    render(<KBPlane knowledgeBases={kbs} onSelect={onSelect} />);
    const rows = screen.getAllByTestId('kb-row');
    fireEvent.click(rows[0]);
    expect(onSelect).toHaveBeenCalledWith(kbs[0]);
    fireEvent.click(rows[1]);
    expect(onSelect).toHaveBeenCalledWith(kbs[1]);
  });
});
