import { describe, it, expect, vi, afterEach } from 'vitest';
import { streamChat } from './api';

function sseStreamResponse(frames) {
  const enc = new TextEncoder();
  let i = 0;
  const body = { getReader: () => ({
    read: () => i < frames.length
      ? Promise.resolve({ value: enc.encode(frames[i++]), done: false })
      : Promise.resolve({ value: undefined, done: true }),
  }) };
  return { ok: true, body };
}

afterEach(() => { vi.restoreAllMocks(); });

describe('streamChat', () => {
  it('parses SSE data frames into onEvent calls', async () => {
    global.fetch = vi.fn().mockResolvedValue(sseStreamResponse([
      'data: {"type":"token","delta":"hi"}\n\n',
      'data: {"type":"done","canceled":false,"text":"hi"}\n\n',
    ]));
    const events = [];
    await streamChat('hello', { onEvent: (e) => events.push(e) });
    expect(events[0]).toEqual({ type: 'token', delta: 'hi' });
    expect(events[1].type).toBe('done');
  });

  it('handles a frame split across reads', async () => {
    global.fetch = vi.fn().mockResolvedValue(sseStreamResponse([
      'data: {"type":"to', 'ken","delta":"x"}\n\n',
      'data: {"type":"done","canceled":false,"text":"x"}\n\n',
    ]));
    const events = [];
    await streamChat('hello', { onEvent: (e) => events.push(e) });
    expect(events[0]).toEqual({ type: 'token', delta: 'x' });
  });
});

describe('streamChat error detail', () => {
  it('surfaces the server reason instead of a bare status', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false, status: 400, body: null,
      json: () => Promise.resolve({ detail: "the current model can't read images" }),
    });
    await expect(streamChat('hi', { onEvent: () => {} }))
      .rejects.toThrow("the current model can't read images");
  });

  it('falls back to the status when the body is not JSON', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false, status: 502, body: null,
      json: () => Promise.reject(new Error('not json')),
    });
    await expect(streamChat('hi', { onEvent: () => {} })).rejects.toThrow('stream failed: 502');
  });
});
