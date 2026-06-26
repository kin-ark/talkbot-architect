import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PageOverlay from './PageOverlay';

describe('PageOverlay', () => {
  it('renders title + children', () => {
    render(<PageOverlay title="Stats" onClose={() => {}}><p>body</p></PageOverlay>);
    expect(screen.getByText('Stats')).toBeInTheDocument();
    expect(screen.getByText('body')).toBeInTheDocument();
  });
  it('close button fires onClose', () => {
    const onClose = vi.fn();
    render(<PageOverlay title="Stats" onClose={onClose}>x</PageOverlay>);
    fireEvent.click(screen.getByTestId('page-close'));
    expect(onClose).toHaveBeenCalled();
  });
  it('clicking the scrim fires onClose', () => {
    const onClose = vi.fn();
    render(<PageOverlay title="Stats" onClose={onClose}>x</PageOverlay>);
    fireEvent.click(screen.getByTestId('page-scrim'));
    expect(onClose).toHaveBeenCalled();
  });
  it('Escape fires onClose', () => {
    const onClose = vi.fn();
    render(<PageOverlay title="Stats" onClose={onClose}>x</PageOverlay>);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
