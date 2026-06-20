import React, { useMemo } from 'react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Minimalist custom node styling can just be default nodes with custom styling
// or we can just use default nodes, but the task says: 
// "Use a minimalist styling for the nodes (white background, thin border)."
// We'll apply this via default node inline styles or a custom node type.
// Since ReactFlow's default node already looks somewhat like this, we'll just style it.

const nodeStyle = {
  background: '#fff',
  border: '1px solid #e2e8f0', // thin border (tailwind gray-200)
  borderRadius: '8px',
  padding: '10px',
  fontSize: '12px',
  color: '#1e293b' // tailwind slate-800
};

export function flattenFlow(mainFlow = []) {
  const nodes = [];
  const edges = [];
  let yOffset = 0;

  mainFlow.forEach((comp, compIdx) => {
    const compId = `comp-${compIdx}`;
    nodes.push({
      id: compId,
      position: { x: 0, y: yOffset },
      data: { label: comp.name },
      style: { ...nodeStyle, fontWeight: 'bold', background: '#f8fafc' }
    });

    let currentY = yOffset + 100;
    
    // BFS/DFS to layout children
    const walk = (nodeList, parentId, depth, xOffsetStart) => {
      let currentX = xOffsetStart;
      nodeList.forEach((node) => {
        const nodeId = node.uuid;
        // avoid duplicates if multiple parents or cycles (though we're building a tree)
        if (!nodes.find(n => n.id === nodeId)) {
          const label = `${node.name} (${node.node_type || 'Unknown'})`;
          nodes.push({
            id: nodeId,
            position: { x: currentX, y: currentY },
            data: { label, originalNode: node },
            style: nodeStyle
          });
        }
        
        edges.push({
          id: `e-${parentId}-${nodeId}`,
          source: parentId,
          target: nodeId,
          type: 'smoothstep'
        });

        if (node.children && node.children.length > 0) {
          const oldY = currentY;
          currentY += 100;
          walk(node.children, nodeId, depth + 1, currentX);
          currentY = oldY; // restore for siblings? 
          // Actually a simple layout is better if we just keep increasing Y for depth.
          // For simplicity, let's just do an incremental X for siblings.
        }
        currentX += 250;
      });
    };

    if (comp.children) {
      walk(comp.children, compId, 1, 0);
    }
    yOffset += 500; // arbitrary spacing between components
  });

  return { nodes, edges };
}

export default function DialogueGraphCanvas({ mainFlow = [], onNodeClick }) {
  const { nodes, edges } = useMemo(() => flattenFlow(mainFlow), [mainFlow]);

  const handleNodeClick = (event, node) => {
    if (onNodeClick) {
      if (node.data && node.data.originalNode) {
        onNodeClick(node.data.originalNode);
      } else {
        // For components or basic nodes without originalNode
        onNodeClick({ name: node.data?.label || 'Component', node_type: 'Component' });
      }
    }
  };

  return (
    <div className="w-full h-full bg-slate-50" data-testid="dialogue-graph-canvas">
      <ReactFlow 
        nodes={nodes} 
        edges={edges} 
        fitView 
        onNodeClick={handleNodeClick}
      >
        <Background color="#ccc" gap={16} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
