import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => vi.clearAllMocks());

describe('useSession rehydrate on mount', () => {
  it('restores summary + transcript when GET /session has a session', async () => {
    api.getSession.mockResolvedValue({
      summary: { components: [], knowledge_bases: [] }, findings: [],
      transcript: [{ role: 'user', text: 'hi' }, { role: 'agent', text: 'hello' }],
      proposal: null, can_undo: true, can_redo: false,
    });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.summary).not.toBeNull());
    expect(result.current.transcript.map((m) => m.text)).toEqual(['hi', 'hello']);
    expect(result.current.canUndo).toBe(true);
  });

  it('does nothing when GET /session has no session', async () => {
    api.getSession.mockResolvedValue({ summary: null });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(api.getSession).toHaveBeenCalled());
    expect(result.current.summary).toBeNull();
    expect(result.current.transcript).toEqual([]);
  });
});
