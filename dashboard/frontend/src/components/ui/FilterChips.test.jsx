import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import FilterChips from './FilterChips';

const opts = [['all', 'All'], ['user', 'User'], ['system', 'System']];

describe('FilterChips', () => {
  it('renders a chip per option', () => {
    render(<FilterChips options={opts} value="all" onChange={() => {}} />);
    expect(screen.getByTestId('filter-chips')).toBeInTheDocument();
    expect(screen.getByTestId('chip-all')).toBeInTheDocument();
    expect(screen.getByTestId('chip-system')).toBeInTheDocument();
  });
  it('marks the active chip', () => {
    render(<FilterChips options={opts} value="user" onChange={() => {}} />);
    expect(screen.getByTestId('chip-user').className).toContain('bg-primary');
    expect(screen.getByTestId('chip-all').className).not.toContain('bg-primary');
  });
  it('fires onChange with the id', () => {
    const onChange = vi.fn();
    render(<FilterChips options={opts} value="all" onChange={onChange} />);
    fireEvent.click(screen.getByTestId('chip-system'));
    expect(onChange).toHaveBeenCalledWith('system');
  });
});
