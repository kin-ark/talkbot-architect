import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import DocsPage from './DocsPage';

describe('DocsPage', () => {
  it('lists topics and shows the first one by default', () => {
    render(<DocsPage onClose={() => {}} />);
    expect(screen.getByRole('button', { name: /Getting Started/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Node types & limits/ })).toBeInTheDocument();
    expect(screen.getByTestId('doc-content').textContent).toMatch(/Talkbot Architect helps you/);
  });

  it('switches content when a topic is clicked', () => {
    render(<DocsPage onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /Chat tips/ }));
    expect(screen.getByTestId('doc-content').textContent).toMatch(/Slash commands/);
  });

  it('renders the inline figure for a sentineled topic', () => {
    render(<DocsPage onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /Node types & limits/ }));
    expect(screen.getByTestId('fig-node-types')).toBeInTheDocument();
  });

  it('Back button fires onClose', () => {
    const onClose = vi.fn();
    render(<DocsPage onClose={onClose} />);
    fireEvent.click(screen.getByTestId('docs-back'));
    expect(onClose).toHaveBeenCalled();
  });

  it('Escape fires onClose', () => {
    const onClose = vi.fn();
    render(<DocsPage onClose={onClose} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
