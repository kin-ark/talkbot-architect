import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Tabs from './Tabs';

const TABS = [{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }, { id: 'c', label: 'C' }];

describe('Tabs a11y', () => {
  it('exposes tablist/tab roles + aria-selected', () => {
    render(<Tabs tabs={TABS} active="b" onChange={() => {}} />);
    expect(screen.getByRole('tablist')).toBeInTheDocument();
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(screen.getByRole('tab', { name: 'B' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'A' })).toHaveAttribute('aria-selected', 'false');
  });

  it('ArrowRight/ArrowLeft move to the adjacent tab (wrapping)', () => {
    const onChange = vi.fn();
    render(<Tabs tabs={TABS} active="c" onChange={onChange} />);
    fireEvent.keyDown(screen.getByRole('tablist'), { key: 'ArrowRight' });
    expect(onChange).toHaveBeenCalledWith('a');   // wraps c -> a
    fireEvent.keyDown(screen.getByRole('tablist'), { key: 'ArrowLeft' });
    expect(onChange).toHaveBeenCalledWith('b');    // c -> b
  });
});
