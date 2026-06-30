import { describe, it, expect, vi, beforeEach } from 'vitest';
import { toast, subscribe, getSnapshot, dismiss } from './toastStore';

beforeEach(() => {
  // clear any leftover toasts between tests
  getSnapshot().slice().forEach((t) => dismiss(t.id));
  vi.useRealTimers();
});

describe('toastStore', () => {
  it('push adds a toast and notifies subscribers', () => {
    const seen = [];
    const unsub = subscribe(() => seen.push(getSnapshot().length));
    toast.success('hi');
    expect(getSnapshot().map((t) => t.message)).toContain('hi');
    expect(seen.length).toBeGreaterThan(0);
    unsub();
  });

  it('mints unique, monotonic ids', () => {
    const a = toast.info('a'); const b = toast.info('b');
    expect(b).toBe(a + 1);
  });

  it('auto-dismisses after the duration', () => {
    vi.useFakeTimers();
    toast.success('bye', { duration: 1000 });
    expect(getSnapshot().some((t) => t.message === 'bye')).toBe(true);
    vi.advanceTimersByTime(1000);
    expect(getSnapshot().some((t) => t.message === 'bye')).toBe(false);
  });

  it('duration 0 is sticky', () => {
    vi.useFakeTimers();
    toast.info('stay', { duration: 0 });
    vi.advanceTimersByTime(60000);
    expect(getSnapshot().some((t) => t.message === 'stay')).toBe(true);
  });

  it('dismiss removes immediately and clears the timer', () => {
    vi.useFakeTimers();
    const id = toast.success('x', { duration: 5000 });
    dismiss(id);
    expect(getSnapshot().some((t) => t.id === id)).toBe(false);
    vi.advanceTimersByTime(5000); // no throw, no resurrection
    expect(getSnapshot().some((t) => t.id === id)).toBe(false);
  });

  it('toast.error defaults to a 6000ms duration', () => {
    vi.useFakeTimers();
    toast.error('boom');
    vi.advanceTimersByTime(5999);
    expect(getSnapshot().some((t) => t.message === 'boom')).toBe(true);
    vi.advanceTimersByTime(1);
    expect(getSnapshot().some((t) => t.message === 'boom')).toBe(false);
  });
});
