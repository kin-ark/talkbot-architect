import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import FlowCanvas from './FlowCanvas';

// @xyflow/react uses ResizeObserver internally; jsdom doesn't include it.
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const summary = { components: [{ uuid: 'c1', name: 'A', root_uuids: ['n1'],
  nodes: { n1: { uuid: 'n1', label: 'Greet', node_type: 'talk', text: 'Hi', referenced_vars: [], allowed_kbs: [], branches: [] } } }],
  knowledge_bases: [] };

describe('FlowCanvas', () => {
  it('renders the canvas container', () => {
    render(<FlowCanvas summary={summary} onSelectNode={() => {}} />);
    expect(screen.getByTestId('flow-canvas')).toBeInTheDocument();
  });
});

describe('TYPE_COLOR node-type contract', () => {
  it('defines colors for conditional and variable_assignment', () => {
    const __dirname = path.dirname(fileURLToPath(import.meta.url));
    const src = fs.readFileSync(
      path.resolve(__dirname, 'FlowCanvas.jsx'), 'utf-8');
    expect(src).toMatch(/conditional:\s*'var\(--c-node-conditional\)'/);
    expect(src).toMatch(/variable_assignment:\s*'var\(--c-node-assign\)'/);
  });

  it('defines colors for nested_component and exit_port', () => {
    const __dirname = path.dirname(fileURLToPath(import.meta.url));
    const src = fs.readFileSync(
      path.resolve(__dirname, 'FlowCanvas.jsx'), 'utf-8');
    expect(src).toMatch(/nested_component:\s*'var\(--c-node-nested\)'/);
    expect(src).toMatch(/exit_port:\s*'var\(--c-node-exit-port\)'/);
  });
});
