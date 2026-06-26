import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => {
  vi.clearAllMocks();
  api.getSession.mockResolvedValue({ summary: null, id: null, bot_name: null });
  api.listSessions.mockResolvedValue({ sessions: [], active_id: null });
});

describe('useSession bot name', () => {
  it('reads bot_name from the rehydrate payload on mount', async () => {
    api.getSession.mockResolvedValue({
      id: 's1', bot_name: 'Debt Collector',
      summary: { components: [], knowledge_bases: [] }, findings: [],
      transcript: [], proposal: null, can_undo: false, can_redo: false,
    });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.botName).toBe('Debt Collector'));
  });

  it('renameBot calls the api and updates botName + undo state', async () => {
    api.getSession.mockResolvedValue({
      id: 's1', bot_name: 'Empty Dialogue',
      summary: { components: [], knowledge_bases: [] }, findings: [],
      transcript: [], proposal: null, can_undo: false, can_redo: false,
    });
    api.setSpeechName.mockResolvedValue({
      ok: true, bot_name: 'Survey Bot',
      summary: { components: [], knowledge_bases: [] }, findings: [],
      can_undo: true, can_redo: false,
    });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.botName).toBe('Empty Dialogue'));
    await act(async () => { await result.current.renameBot('Survey Bot'); });
    expect(api.setSpeechName).toHaveBeenCalledWith('Survey Bot');
    expect(result.current.botName).toBe('Survey Bot');
    expect(result.current.canUndo).toBe(true);
  });
});
