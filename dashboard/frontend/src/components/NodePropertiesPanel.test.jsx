import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import NodePropertiesPanel from './NodePropertiesPanel';

describe('NodePropertiesPanel', () => {
  it('renders nothing if no selected node', () => {
    const { container } = render(<NodePropertiesPanel selectedNode={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders properties of selected node', () => {
    const node = {
      name: 'Welcome Node',
      node_type: 'Talk',
      allowedKBs: ['KB-1']
    };
    const kbs = [
      { id: 'KB-1', title: 'Test KB Title' }
    ];

    render(<NodePropertiesPanel selectedNode={node} knowledgeBases={kbs} />);
    
    expect(screen.getByTestId('node-properties-panel')).toBeInTheDocument();
    expect(screen.getByTestId('prop-label').textContent).toBe('Welcome Node');
    expect(screen.getByTestId('prop-type').textContent).toBe('Talk');
    
    const kbItems = screen.getByTestId('prop-kbs');
    expect(kbItems).toBeInTheDocument();
    expect(kbItems.textContent).toContain('Test KB Title');
  });

  it('handles missing KB titles gracefully by displaying ID', () => {
    const node = {
      name: 'Unknown Node',
      node_type: 'Talk',
      allowedKBs: ['KB-999']
    };

    render(<NodePropertiesPanel selectedNode={node} knowledgeBases={[]} />);
    
    const kbItems = screen.getByTestId('prop-kbs');
    expect(kbItems.textContent).toContain('KB-999');
  });

  it('displays None when there are no allowed KBs', () => {
    const node = {
      name: 'Start',
      node_type: 'Root',
      allowedKBs: []
    };

    render(<NodePropertiesPanel selectedNode={node} />);
    
    expect(screen.getByTestId('prop-no-kbs')).toBeInTheDocument();
    expect(screen.getByTestId('prop-no-kbs').textContent).toBe('None');
  });
});
