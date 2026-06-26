import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DocumentationPage from './DocumentationPage';

describe('DocumentationPage', () => {
  it('lists every topic in the sidebar', () => {
    render(<DocumentationPage />);
    expect(screen.getByRole('button', { name: 'Getting Started' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Node types & limits' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Chat tips' })).toBeInTheDocument();
  });
  it('shows the first topic body by default', () => {
    render(<DocumentationPage />);
    expect(screen.getByTestId('doc-content').textContent).toMatch(/Talkbot Architect helps you/);
  });
  it('clicking a topic switches the content', () => {
    render(<DocumentationPage />);
    fireEvent.click(screen.getByRole('button', { name: 'Chat tips' }));
    expect(screen.getByTestId('doc-content').textContent).toMatch(/Slash commands/);
  });
});
