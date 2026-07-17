import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RecoveryBar from './RecoveryBar';

describe('RecoveryBar', () => {
  it('renders a button per token in order and fires the handler', () => {
    const onFix = vi.fn(); const onDiscard = vi.fn();
    render(<RecoveryBar tokens={['fix', 'discard']} onFix={onFix} onDiscard={onDiscard} />);
    const btns = screen.getAllByRole('button');
    expect(btns.map((b) => b.textContent.trim())).toEqual(['Fix errors', 'Discard']);
    fireEvent.click(screen.getByText('Fix errors'));
    expect(onFix).toHaveBeenCalled();
  });
  it('renders nothing for an empty token list', () => {
    const { container } = render(<RecoveryBar tokens={[]} />);
    expect(container.firstChild).toBeNull();
  });
  it('renders Continue with its handler', () => {
    const onContinue = vi.fn();
    render(<RecoveryBar tokens={['continue']} onContinue={onContinue} />);
    fireEvent.click(screen.getByText('Continue'));
    expect(onContinue).toHaveBeenCalled();
  });
});
