import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import NodePropertiesPanel from './NodePropertiesPanel';

const NODE = { uuid: 'n1', label: 'Greet', node_type: 'talk', text: 'Hi {Name}',
  referenced_vars: ['Name'], allowed_kbs: [], branches: [{ label: 'Positive', kind: 'intent' }] };

describe('NodePropertiesPanel', () => {
  it('shows node type, text and branches', () => {
    render(<NodePropertiesPanel node={NODE} summary={{ knowledge_bases: [] }} onEditNode={() => {}} />);
    expect(screen.getByText('talk')).toBeInTheDocument();
    expect(screen.getByText(/Hi \{Name\}/)).toBeInTheDocument();
    expect(screen.getByText('Positive')).toBeInTheDocument();
  });

  it('editing the label and saving fires onEditNode(uuid,{label})', () => {
    const onEditNode = vi.fn();
    render(<NodePropertiesPanel node={NODE} summary={{ knowledge_bases: [] }} onEditNode={onEditNode} />);
    fireEvent.click(screen.getByTestId('edit-label'));
    const input = screen.getByTestId('label-input');
    fireEvent.change(input, { target: { value: 'Greeting' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onEditNode).toHaveBeenCalledWith('n1', { label: 'Greeting' });
  });

  it('editing the dialogue and saving fires onEditNode(uuid,{prompt})', () => {
    const onEditNode = vi.fn();
    render(<NodePropertiesPanel node={NODE} summary={{ knowledge_bases: [] }} onEditNode={onEditNode} />);
    fireEvent.click(screen.getByTestId('edit-dialogue'));
    fireEvent.change(screen.getByTestId('dialogue-input'), { target: { value: 'Hello there' } });
    fireEvent.click(screen.getByTestId('dialogue-save'));
    expect(onEditNode).toHaveBeenCalledWith('n1', { prompt: 'Hello there' });
  });

  it('empty or unchanged save is a no-op', () => {
    const onEditNode = vi.fn();
    render(<NodePropertiesPanel node={NODE} summary={{ knowledge_bases: [] }} onEditNode={onEditNode} />);
    fireEvent.click(screen.getByTestId('edit-label'));
    const input = screen.getByTestId('label-input');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onEditNode).not.toHaveBeenCalled();
  });

  it('hides the dialogue editor for a node with no text', () => {
    const noText = { uuid: 'e1', label: 'Exit', node_type: 'exit', branches: [] };
    render(<NodePropertiesPanel node={noText} summary={{ knowledge_bases: [] }} onEditNode={() => {}} />);
    expect(screen.queryByTestId('edit-dialogue')).toBeNull();
    expect(screen.getByTestId('edit-label')).toBeInTheDocument();   // label still editable
  });
});
