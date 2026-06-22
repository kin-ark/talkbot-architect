import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import NodePropertiesPanel from './NodePropertiesPanel';

describe('NodePropertiesPanel', () => {
  it('shows node type, text and branches', () => {
    render(<NodePropertiesPanel node={{ uuid: 'n1', label: 'Greet', node_type: 'talk', text: 'Hi {Name}',
      referenced_vars: ['Name'], allowed_kbs: [], branches: [{ label: 'Positive', kind: 'intent' }] }} summary={{ knowledge_bases: [] }} />);
    expect(screen.getByText('talk')).toBeInTheDocument();
    expect(screen.getByText(/Hi \{Name\}/)).toBeInTheDocument();
    expect(screen.getByText('Positive')).toBeInTheDocument();
  });
});
