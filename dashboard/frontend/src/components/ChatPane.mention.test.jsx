import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

const SUMMARY = { components: [
  { uuid: 'cA', name: 'Greeting', nodes: { n1: { uuid: 'n1', label: 'AskName' } } },
  { uuid: 'cB', name: 'Payment', nodes: { n2: { uuid: 'n2', label: 'Charge' } } },
], knowledge_bases: [] };
const base = { transcript: [], proposal: null, sending: false, onSend: () => {},
  onApply: () => {}, onReject: () => {}, onCancel: () => {} };

describe('ChatPane @-mention', () => {
  it('typing "@" lists components and nodes from the summary', () => {
    render(<ChatPane {...base} summary={SUMMARY} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about/i), { target: { value: 'edit @' } });
    expect(screen.getByTestId('mention-menu')).toBeInTheDocument();
    // richer mention rows render the component label AND "in Greeting" on its
    // node row, so /Greeting/ now matches more than once.
    expect(screen.getAllByText(/Greeting/).length).toBeGreaterThan(0);
    expect(screen.getByText(/AskName/)).toBeInTheDocument();
  });
  it('filters by the text after @', () => {
    render(<ChatPane {...base} summary={SUMMARY} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about/i), { target: { value: '@Charge' } });
    const menu = screen.getByTestId('mention-menu');
    expect(menu).toBeInTheDocument();
    expect(menu.textContent).toContain('Charge');
    expect(menu.textContent).not.toContain('AskName');
  });
  it('selecting a node inserts "@label (uuid)" into the input', () => {
    render(<ChatPane {...base} summary={SUMMARY} />);
    const input = screen.getByPlaceholderText(/ask about/i);
    fireEvent.change(input, { target: { value: 'change @Ask' } });
    fireEvent.click(screen.getByText(/AskName/));
    expect(input.value).toBe('change @AskName (n1) ');
  });
});
