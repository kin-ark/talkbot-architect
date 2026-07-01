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

  it('renders an activity row per entry when expanded', () => {
    render(<ToolTrace trace={[{ name: 'validate', status: 'done' }, { name: 'add_node', status: 'done' }]} />);
    fireEvent.click(screen.getByTestId('tool-trace-toggle'));
    expect(screen.getAllByTestId('activity-row')).toHaveLength(2);
  });

  it('shows a running narration line while an entry is running, gone when all done', () => {
    const { rerender } = render(<ToolTrace trace={[{ name: 'build', status: 'running' }]} />);
    expect(screen.getByTestId('activity-running').textContent).toMatch(/Building from manifest/);
    rerender(<ToolTrace trace={[{ name: 'build', status: 'done' }]} />);
    expect(screen.queryByTestId('activity-running')).toBeNull();
  });
});
