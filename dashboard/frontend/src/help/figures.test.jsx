import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { figures } from './figures';

describe('figures registry', () => {
  const ids = ['layout', 'node-types', 'proposal-flow', 'severity', 'kb-flow'];

  it('exposes exactly the expected figure ids', () => {
    expect(Object.keys(figures).sort()).toEqual([...ids].sort());
  });

  it.each(ids)('figure "%s" renders an svg inside a fig-<id> figure', (id) => {
    const Fig = figures[id];
    const { container, getByTestId } = render(<Fig />);
    expect(getByTestId(`fig-${id}`)).toBeInTheDocument();
    expect(container.querySelector('svg')).not.toBeNull();
  });
});
