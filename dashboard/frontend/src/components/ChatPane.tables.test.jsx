import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { proposal: null, sending: false, onSend: () => {}, onApply: () => {},
  onReject: () => {}, onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

const TABLE_MD = `| A | B |\n| - | - |\n| 1 | 2 |`;

describe('ChatPane tables + inline code', () => {
  it('wraps a markdown table in a horizontal-scroll container', () => {
    const { getByTestId, container } = render(
      <ChatPane {...base} transcript={[{ role: 'agent', text: TABLE_MD }]} />);
    const scroll = getByTestId('md-table-scroll');
    expect(scroll.className).toContain('overflow-x-auto');
    expect(scroll.querySelector('table')).not.toBeNull();
    expect(container.querySelectorAll('td').length).toBe(2);
  });

  it('styles inline code distinctly (mono + token bg class)', () => {
    const { container } = render(
      <ChatPane {...base} transcript={[{ role: 'agent', text: 'use `npm run dev` now' }]} />);
    const code = container.querySelector('code');
    expect(code).not.toBeNull();
    expect(code.className).toMatch(/font-mono|bg-surface-muted/);
  });
});
