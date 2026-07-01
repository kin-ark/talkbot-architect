import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatInput from './ChatInput';

const base = {
  value: '', onChange: () => {}, onSubmit: () => {}, sending: false, onCancel: () => {},
  slashMatches: [], mentionMatches: [], onPickSlash: () => {}, onPickMention: () => {},
};

const ta = () => screen.getByPlaceholderText(/ask about/i);

describe('ChatInput', () => {
  it('Enter submits when there is text and no menu open', () => {
    const onSubmit = vi.fn();
    render(<ChatInput {...base} value="hi" onSubmit={onSubmit} />);
    fireEvent.keyDown(ta(), { key: 'Enter' });
    expect(onSubmit).toHaveBeenCalled();
  });

  it('Shift+Enter does NOT submit', () => {
    const onSubmit = vi.fn();
    render(<ChatInput {...base} value="hi" onSubmit={onSubmit} />);
    fireEvent.keyDown(ta(), { key: 'Enter', shiftKey: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('Enter on empty/whitespace does not submit', () => {
    const onSubmit = vi.fn();
    render(<ChatInput {...base} value="   " onSubmit={onSubmit} />);
    fireEvent.keyDown(ta(), { key: 'Enter' });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('Enter with an open slash menu picks the first match instead of submitting', () => {
    const onSubmit = vi.fn(); const onPickSlash = vi.fn();
    render(<ChatInput {...base} value="/v" onSubmit={onSubmit} onPickSlash={onPickSlash}
      slashMatches={[{ cmd: '/validate', mode: 'send', text: 'x' }]} />);
    fireEvent.keyDown(ta(), { key: 'Enter' });
    expect(onPickSlash).toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('Escape dismisses an open menu', () => {
    render(<ChatInput {...base} value="/v" slashMatches={[{ cmd: '/validate', mode: 'send', text: 'x' }]} />);
    expect(screen.getByTestId('slash-menu')).toBeInTheDocument();
    fireEvent.keyDown(ta(), { key: 'Escape' });
    expect(screen.queryByTestId('slash-menu')).toBeNull();
  });

  it('ignores Enter during IME composition', () => {
    const onSubmit = vi.fn();
    render(<ChatInput {...base} value="hi" onSubmit={onSubmit} />);
    fireEvent.keyDown(ta(), { key: 'Enter', isComposing: true });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('auto-grows: sets an explicit height on input', () => {
    render(<ChatInput {...base} value="line1" />);
    const el = ta();
    Object.defineProperty(el, 'scrollHeight', { configurable: true, value: 120 });
    fireEvent.input(el, { target: { value: 'line1\nline2' } });
    expect(el.style.height).toBe('120px');
  });
});
