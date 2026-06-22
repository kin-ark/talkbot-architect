import React from 'react';
export default function NodePropertiesPanel({ node }) {
  return <div data-testid="node-properties-panel">{node ? node.label : 'Select a node'}</div>;
}
