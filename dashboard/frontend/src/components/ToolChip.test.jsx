import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ToolChip from './ToolChip';

describe('ToolChip', () => {
  it('has a friendly label for every current tool', () => {
    const tools = ['validate','summarize','read_node','get_facts','get_schema','scaffold_bot',
      'build','add_component','add_node','connect_components','add_intent','add_variable',
      'apply_mods','set_path','delete_path'];
    for (const name of tools) {
      const { container, unmount } = render(<ToolChip name={name} args={{}} />);
      // label must not be the raw tool name (i.e. it was mapped)
      expect(container.textContent).not.toBe(name);
      unmount();
    }
  });
  it('shows the summary when done', () => {
    render(<ToolChip name="validate" args={{}} status="done" summary="3 findings" />);
    expect(screen.getByText(/3 findings/)).toBeInTheDocument();
  });
});
