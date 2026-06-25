import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => { vi.clearAllMocks(); api.getSession.mockResolvedValue({ summary: null }); });

describe('useSession retry', () => {
  it('retry resends the last user message', async () => {
    const seen = [];
    api.streamChat.mockImplementation(async (msg, { onEvent }) => {
      seen.push(msg); onEvent({ type: 'done', canceled: false, text: 'ok' });
    });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('first'); });
    await act(async () => { await result.current.retry(); });
    expect(seen).toEqual(['first', 'first']);
    const users = result.current.transcript.filter((m) => m.role === 'user');
    expect(users.map((m) => m.text)).toEqual(['first', 'first']);
  });
});
