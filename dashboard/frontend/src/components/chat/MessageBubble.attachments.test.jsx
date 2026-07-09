import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MessageBubble from './MessageBubble';

describe('MessageBubble attachments', () => {
  it('renders image thumbnails as new-tab links', () => {
    render(<MessageBubble role="user" text="look"
      images={[{ name: 'a.png', url: 'blob:a' }]} file={null} />);
    const img = screen.getByAltText('a.png');
    expect(img.getAttribute('src')).toBe('blob:a');
    const link = img.closest('a');
    expect(link.getAttribute('href')).toBe('blob:a');
    expect(link.getAttribute('target')).toBe('_blank');
    expect(link.getAttribute('rel')).toBe('noopener noreferrer');
  });

  it('renders a file chip as a download link', () => {
    render(<MessageBubble role="user" text="" images={[]} file={{ name: 'kb.xls', url: 'blob:f' }} />);
    const link = screen.getByText(/kb\.xls/).closest('a');
    expect(link.getAttribute('href')).toBe('blob:f');
    expect(link.getAttribute('rel')).toBe('noopener noreferrer');
  });

  it('agent bubble without attachments is unchanged', () => {
    render(<MessageBubble role="agent" text="hi" />);
    expect(screen.queryByRole('img')).toBeNull();
  });
});
