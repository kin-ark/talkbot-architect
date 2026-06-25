import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { transcript: [], proposal: null, sending: false, onApply: () => {},
  onReject: () => {}, onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

describe('ChatPane slash-commands', () => {
  it('typing "/" opens the slash menu', () => {
    render(<ChatPane {...base} onSend={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about/i), { target: { value: '/' } });
    expect(screen.getByTestId('slash-menu')).toBeInTheDocument();
    expect(screen.getByText('/validate')).toBeInTheDocument();
  });
  it('selecting /validate sends its prompt', () => {
    const onSend = vi.fn();
    render(<ChatPane {...base} onSend={onSend} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about/i), { target: { value: '/val' } });
    fireEvent.click(screen.getByText('/validate'));
    expect(onSend).toHaveBeenCalledWith('Validate the dialogue and list all findings.');
  });
  it('selecting /add-node fills the input without sending', () => {
    const onSend = vi.fn();
    render(<ChatPane {...base} onSend={onSend} />);
    fireEvent.change(screen.getByPlaceholderText(/ask about/i), { target: { value: '/add' } });
    fireEvent.click(screen.getByText('/add-node'));
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByPlaceholderText(/ask about/i).value).toMatch(/add a node/i);
  });
});
