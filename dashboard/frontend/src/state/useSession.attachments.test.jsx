import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => vi.clearAllMocks());

function scriptStream(events) {
  api.streamChat.mockImplementation(async (_msg, { onEvent }) => {
    for (const e of events) onEvent(e);
  });
}

describe('useSession attachments', () => {
  it('send(payload) puts images on the user bubble', async () => {
    scriptStream([
      { type: 'done', canceled: false, text: 'ok' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send({ text: 'look', images: [{ name: 'a.png', url: 'blob:a' }] }); });
    const userMsg = result.current.transcript.find((m) => m.role === 'user');
    expect(userMsg.images).toEqual([{ name: 'a.png', url: 'blob:a' }]);
    expect(userMsg.text).toBe('look');
  });

  it('send(string) is normalized (no images)', async () => {
    scriptStream([
      { type: 'done', canceled: false, text: 'ok' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('plain'); });
    const userMsg = result.current.transcript.find((m) => m.role === 'user');
    expect(userMsg.text).toBe('plain');
    expect(userMsg.images || []).toEqual([]);
  });

  it('reset revokes tracked object URLs', async () => {
    const spy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    scriptStream([
      { type: 'done', canceled: false, text: 'ok' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send({ text: 'x', images: [{ name: 'a.png', url: 'blob:z' }] }); });
    await act(async () => { await result.current.reset(); });
    expect(spy).toHaveBeenCalledWith('blob:z');
    spy.mockRestore();
  });
});
