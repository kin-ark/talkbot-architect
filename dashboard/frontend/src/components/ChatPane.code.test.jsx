import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { proposal: null, sending: false, onSend: () => {}, onApply: () => {},
  onReject: () => {}, onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

const CODE_MD = '```js\nconst x = 1;\n```';

beforeEach(() => {
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue() } });
});

describe('ChatPane code blocks', () => {
  it('highlights fenced code (hljs class present)', () => {
    const { container } = render(<ChatPane {...base} transcript={[{ role: 'agent', text: CODE_MD }]} />);
    expect(container.querySelector('code.hljs, code[class*="hljs"]')).not.toBeNull();
  });

  it('copy button copies the code text', async () => {
    render(<ChatPane {...base} transcript={[{ role: 'agent', text: CODE_MD }]} />);
    fireEvent.click(screen.getByTestId('copy-code'));
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalled());
    expect(navigator.clipboard.writeText.mock.calls[0][0]).toContain('const x = 1;');
  });
});
