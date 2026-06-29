import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => {
  vi.clearAllMocks();
  api.getSession.mockResolvedValue({
    summary: { components: [], knowledge_bases: [] },
    findings: [{ severity: 'error' }],
    transcript: [{ role: 'user', text: 'hi' }],
    proposal: null, can_undo: true, can_redo: false, bot_name: 'Old Bot', id: 's1',
  });
  api.listSessions.mockResolvedValue({ sessions: [{ id: 's1', name: 'A', updated: 1 }], active_id: 's1' });
});

describe('useSession startNew', () => {
  it('clears the local view but preserves the session list and does not clear the backend', async () => {
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.summary).not.toBeNull());
    await waitFor(() => expect(result.current.sessions.length).toBe(1));

    act(() => { result.current.startNew(); });

    expect(result.current.summary).toBeNull();
    expect(result.current.findings).toEqual([]);
    expect(result.current.transcript).toEqual([]);
    expect(result.current.proposal).toBeNull();
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.botName).toBeNull();
    // preserved:
    expect(result.current.sessions.length).toBe(1);
    expect(result.current.activeSessionId).toBe('s1');
    // backend NOT cleared:
    expect(api.clearSession).not.toHaveBeenCalled();
  });
});
