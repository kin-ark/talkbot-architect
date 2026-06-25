import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { proposal: null, sending: false, onApply: () => {}, onReject: () => {},
  onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

describe('ChatPane suggestions', () => {
  it('renders quick-action chips', () => {
    render(<ChatPane {...base} transcript={[]} onSend={() => {}} />);
    expect(screen.getByText('Validate')).toBeInTheDocument();
    expect(screen.getByText('Explain this bot')).toBeInTheDocument();
  });
  it('clicking a chip sends its prompt', () => {
    const onSend = vi.fn();
    render(<ChatPane {...base} transcript={[]} onSend={onSend} />);
    fireEvent.click(screen.getByText('Find problems'));
    expect(onSend).toHaveBeenCalledWith(expect.stringMatching(/problem|finding|issue/i));
  });
});
