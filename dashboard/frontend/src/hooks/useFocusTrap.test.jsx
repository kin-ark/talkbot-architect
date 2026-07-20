import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useRef } from 'react';
import { useFocusTrap } from './useFocusTrap';

function Modal() {
  const ref = useRef(null);
  useFocusTrap(ref);
  return (
    <div ref={ref} tabIndex={-1}>
      <button>first</button>
      <button>last</button>
    </div>
  );
}

describe('useFocusTrap', () => {
  it('focuses the first focusable on mount', () => {
    render(<Modal />);
    expect(screen.getByText('first')).toHaveFocus();
  });

  it('wraps Tab from last back to first', () => {
    render(<Modal />);
    const last = screen.getByText('last');
    last.focus();
    fireEvent.keyDown(last, { key: 'Tab' });
    expect(screen.getByText('first')).toHaveFocus();
  });

  it('wraps Shift+Tab from first back to last', () => {
    render(<Modal />);
    const first = screen.getByText('first');
    first.focus();
    fireEvent.keyDown(first, { key: 'Tab', shiftKey: true });
    expect(screen.getByText('last')).toHaveFocus();
  });

  it('restores focus to the trigger on unmount', () => {
    const trigger = document.createElement('button');
    document.body.appendChild(trigger);
    trigger.focus();
    const { unmount } = render(<Modal />);
    unmount();
    expect(trigger).toHaveFocus();
    trigger.remove();
  });
});
