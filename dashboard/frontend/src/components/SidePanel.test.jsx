import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SidePanel from './SidePanel';

describe('SidePanel', () => {
  it('switches to Findings tab', () => {
    render(<SidePanel summary={{ components: [], knowledge_bases: [] }}
      findings={[{ code: 'WIZ301', severity: 'error', message: 'x' }]}
      selectedNode={null} onSelectNode={() => {}} />);
    fireEvent.click(screen.getByText(/Findings/));
    expect(screen.getByText('WIZ301')).toBeInTheDocument();
  });
});
