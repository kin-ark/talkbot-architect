import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => {
  vi.clearAllMocks();
  api.getSession.mockResolvedValue({ summary: null });
  api.clearSession.mockResolvedValue({ cleared: true });
});

describe('useSession reset', () => {
  it('reset clears the backend + local session state', async () => {
    // start from a rehydrated session
    api.getSession.mockResolvedValue({
      summary: { components: [], knowledge_bases: [] }, findings: [{ severity: 'error' }],
      transcript: [{ role: 'user', text: 'hi' }], proposal: null, can_undo: true, can_redo: false,
    });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.summary).not.toBeNull());

    await act(async () => { await result.current.reset(); });

    expect(api.clearSession).toHaveBeenCalled();
    expect(result.current.summary).toBeNull();
    expect(result.current.transcript).toEqual([]);
    expect(result.current.findings).toEqual([]);
    expect(result.current.canUndo).toBe(false);
  });
});
