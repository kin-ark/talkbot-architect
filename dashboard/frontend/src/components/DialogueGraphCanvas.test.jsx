import React from 'react';
import { render, screen } from '@testing-library/react';
import DialogueGraphCanvas, { flattenFlow } from './DialogueGraphCanvas';
import { ReactFlowProvider } from '@xyflow/react';

// Mock ResizeObserver for React Flow
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const mockMainFlow = [
  {
    name: 'Component 1',
    children: [
      {
        name: 'Root Node',
        uuid: 'root-1',
        node_type: 'Talk',
        allowedKBs: [],
        children: [
          {
            name: 'Child Node',
            uuid: 'child-1',
            node_type: 'Talk',
            allowedKBs: [],
            children: []
          }
        ]
      }
    ]
  }
];

describe('DialogueGraphCanvas', () => {
  it('flattens mainFlow into nodes and edges', () => {
    const { nodes, edges } = flattenFlow(mockMainFlow);
    expect(nodes.length).toBe(3); // Component + Root + Child
    expect(edges.length).toBe(2); // Component -> Root, Root -> Child
    expect(nodes.some(n => n.id === 'root-1')).toBe(true);
    expect(nodes.some(n => n.id === 'child-1')).toBe(true);
  });

  it('renders correctly', () => {
    render(
      <ReactFlowProvider>
        <div style={{ height: 500, width: 500 }}>
          <DialogueGraphCanvas mainFlow={mockMainFlow} />
        </div>
      </ReactFlowProvider>
    );
    expect(screen.getByTestId('dialogue-graph-canvas')).toBeInTheDocument();
  });
});
