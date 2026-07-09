import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ChatInput from './ChatInput';

vi.mock('../../api', () => ({
  attachFile: vi.fn(), clearAttachment: vi.fn(), clearImage: vi.fn(),
}));

const base = {
  value: '', onChange: () => {}, onSubmit: () => {}, sending: false, onCancel: () => {},
  slashMatches: [], mentionMatches: [], onPickSlash: () => {}, onPickMention: () => {},
  canSendImages: true,
};

describe('ChatInput image paste', () => {
  beforeEach(() => vi.clearAllMocks());

  it('uploads a pasted image and shows a thumbnail chip', async () => {
    const { attachFile } = await import('../../api');
    attachFile.mockResolvedValue({ name: 'pasted.png', kind: 'image', count: 1 });
    render(<ChatInput {...base} />);
    const ta = screen.getByPlaceholderText(/ask about/i);
    const file = new File([new Uint8Array([1, 2, 3])], 'pasted.png', { type: 'image/png' });
    fireEvent.paste(ta, { clipboardData: { items: [{ kind: 'file', type: 'image/png', getAsFile: () => file }], files: [file] } });
    await waitFor(() => expect(attachFile).toHaveBeenCalled());
    expect(await screen.findByTestId('image-chip')).toBeTruthy();
  });

  it('disables image attach when model has no vision', () => {
    render(<ChatInput {...base} canSendImages={false} />);
    expect(screen.getByTestId('no-vision-hint')).toBeTruthy();
  });

  it('submits a payload with text + images', async () => {
    const { attachFile } = await import('../../api');
    attachFile.mockResolvedValue({ name: 'p.png', kind: 'image', count: 1 });
    const onSubmit = vi.fn();
    render(<ChatInput {...base} value="hello" onSubmit={onSubmit} />);
    const ta = screen.getByPlaceholderText(/ask about/i);
    const file = new File([new Uint8Array([1])], 'p.png', { type: 'image/png' });
    fireEvent.paste(ta, { clipboardData: { items: [{ kind: 'file', type: 'image/png', getAsFile: () => file }], files: [file] } });
    await screen.findByTestId('image-chip');
    fireEvent.submit(screen.getByTestId('chat-form'));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      text: 'hello', images: expect.arrayContaining([expect.objectContaining({ name: 'p.png' })]),
    }));
  });

  it('allows image-only submit (no text)', async () => {
    const { attachFile } = await import('../../api');
    attachFile.mockResolvedValue({ name: 'p.png', kind: 'image', count: 1 });
    const onSubmit = vi.fn();
    render(<ChatInput {...base} value="" onSubmit={onSubmit} />);
    const ta = screen.getByPlaceholderText(/ask about/i);
    const file = new File([new Uint8Array([1])], 'p.png', { type: 'image/png' });
    fireEvent.paste(ta, { clipboardData: { items: [{ kind: 'file', type: 'image/png', getAsFile: () => file }], files: [file] } });
    await screen.findByTestId('image-chip');
    fireEvent.submit(screen.getByTestId('chat-form'));
    expect(onSubmit).toHaveBeenCalled();
  });
});
