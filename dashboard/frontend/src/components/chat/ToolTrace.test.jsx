import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ToolTrace from './ToolTrace';

describe('ToolTrace', () => {
  it('renders nothing for empty trace', () => {
    const { container } = render(<ToolTrace trace={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('is collapsed by default and expands on toggle', () => {
    render(<ToolTrace trace={[{ name: 'validate', status: 'done' }]} />);
    expect(screen.queryByTestId('tool-trace')).toBeNull();
    fireEvent.click(screen.getByTestId('tool-trace-toggle'));
    expect(screen.getByTestId('tool-trace')).toBeInTheDocument();
  });

  it('auto-expands when a tool is running', () => {
    render(<ToolTrace trace={[{ name: 'build', status: 'running' }]} />);
    expect(screen.getByTestId('tool-trace')).toBeInTheDocument();
  });
});
