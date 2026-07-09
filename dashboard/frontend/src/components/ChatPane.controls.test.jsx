import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

describe('ChatPane controls', () => {
  it('shows Stop while sending and calls onCancel', () => {
    const onCancel = vi.fn();
    render(<ChatPane transcript={[]} proposal={null} sending={true}
      onSend={() => {}} onApply={() => {}} onReject={() => {}} onCancel={onCancel} />);
    const stop = screen.getByText(/stop/i);
    fireEvent.click(stop);
    expect(onCancel).toHaveBeenCalled();
  });

  it('renders an error bubble', () => {
    render(<ChatPane transcript={[{ role: 'error', text: 'boom happened' }]} proposal={null}
      sending={false} onSend={() => {}} onApply={() => {}} onReject={() => {}} onCancel={() => {}} />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
