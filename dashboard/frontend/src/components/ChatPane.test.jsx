import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import ChatPane from './ChatPane';

describe('ChatPane', () => {
  it('renders messages and submits input', () => {
    const onSend = vi.fn();
    render(<ChatPane transcript={[{ role: 'agent', text: 'hello' }]} proposal={null}
      onSend={onSend} onApply={() => {}} onReject={() => {}} />);
    expect(screen.getByText('hello')).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText(/ask/i), { target: { value: 'check' } });
    fireEvent.submit(screen.getByTestId('chat-form'));
    expect(onSend).toHaveBeenCalledWith(expect.objectContaining({ text: 'check' }));
  });

  it('suggestion chips pass strings to onSend', () => {
    const onSend = vi.fn();
    render(<ChatPane transcript={[{ role: 'agent', text: 'hello' }]} proposal={null}
      onSend={onSend} onApply={() => {}} onReject={() => {}} />);
    fireEvent.click(screen.getByText('Validate'));
    expect(onSend).toHaveBeenCalledWith('Validate the dialogue and list all findings.');
  });
});
