import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';
import IconButton from './IconButton';
import Tabs from './Tabs';
import Card from './Card';
import Badge from './Badge';

describe('ui primitives', () => {
  it('Button primary uses token classes + fires onClick', () => {
    const onClick = vi.fn();
    render(<Button variant="primary" onClick={onClick}>Save</Button>);
    const b = screen.getByText('Save');
    expect(b.className).toContain('bg-primary');
    fireEvent.click(b);
    expect(onClick).toHaveBeenCalled();
  });

  it('IconButton sets aria-label', () => {
    render(<IconButton label="settings">⚙</IconButton>);
    expect(screen.getByLabelText('settings')).toBeInTheDocument();
  });

  it('Tabs renders tabs, marks active, fires onChange', () => {
    const onChange = vi.fn();
    render(<Tabs tabs={[{ id: 'a', label: 'Chat' }, { id: 'b', label: 'Findings', badge: 2 }]}
      active="a" onChange={onChange} />);
    expect(screen.getByText('Findings')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Findings'));
    expect(onChange).toHaveBeenCalledWith('b');
  });

  it('Card + Badge render with token classes', () => {
    const { container } = render(<Card><Badge tone="error">err</Badge></Card>);
    expect(container.querySelector('.bg-surface')).toBeTruthy();
    expect(screen.getByText('err').className).toContain('text-error');
  });
});
