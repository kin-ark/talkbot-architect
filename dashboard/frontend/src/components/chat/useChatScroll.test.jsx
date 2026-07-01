import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useChatScroll } from './useChatScroll';

function makeEl({ scrollHeight = 1000, clientHeight = 300, scrollTop = 0 } = {}) {
  return { scrollHeight, clientHeight, scrollTop, scrollTo({ top }) { this.scrollTop = top; } };
}

describe('useChatScroll', () => {
  it('atBottom is true when scrolled near the bottom', () => {
    const { result } = renderHook(() => useChatScroll(0));
    result.current.scrollRef.current = makeEl({ scrollTop: 700 }); // 1000-700-300=0 <80
    act(() => result.current.onScroll());
    expect(result.current.atBottom).toBe(true);
  });

  it('atBottom is false when scrolled up', () => {
    const { result } = renderHook(() => useChatScroll(0));
    result.current.scrollRef.current = makeEl({ scrollTop: 100 }); // 1000-100-300=600 >=80
    act(() => result.current.onScroll());
    expect(result.current.atBottom).toBe(false);
  });

  it('scrollToBottom scrolls the container and marks atBottom', () => {
    const { result } = renderHook(() => useChatScroll(0));
    const el = makeEl({ scrollTop: 0 });
    result.current.scrollRef.current = el;
    act(() => result.current.scrollToBottom());
    expect(el.scrollTop).toBe(el.scrollHeight);
    expect(result.current.atBottom).toBe(true);
  });
});
