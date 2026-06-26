import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => {
  vi.clearAllMocks();
  api.getSession.mockResolvedValue({ summary: null, id: null });
  api.listSessions.mockResolvedValue({ sessions: [], active_id: null });
});

describe('useSession session list', () => {
  it('populates sessions + activeSessionId on mount', async () => {
    api.getSession.mockResolvedValue({
      id: 's1', summary: { components: [], knowledge_bases: [] }, findings: [],
      transcript: [], proposal: null, can_undo: false, can_redo: false,
      usage: { input_tokens: 10, output_tokens: 4, turns: 1, model: 'm-x' },
    });
    api.listSessions.mockResolvedValue({
      sessions: [{ id: 's1', name: 'A', updated: 2, usage: {} },
                 { id: 's2', name: 'B', updated: 1, usage: {} }],
      active_id: 's1',
    });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.sessions.length).toBe(2));
    expect(result.current.activeSessionId).toBe('s1');
    expect(result.current.usage).toEqual({ input_tokens: 10, output_tokens: 4, turns: 1, model: 'm-x' });
  });

  it('switchSession applies the activated payload', async () => {
    api.activateSession.mockResolvedValue({
      id: 's2', summary: { components: [{ uuid: 'c', name: 'X', nodes: {} }], knowledge_bases: [] },
      findings: [{ severity: 'error' }], transcript: [{ role: 'agent', text: 'switched' }],
      proposal: null, can_undo: true, can_redo: false,
      usage: { input_tokens: 7, output_tokens: 3, turns: 2, model: 'm-y' },
    });
    api.listSessions.mockResolvedValue({ sessions: [{ id: 's2', name: 'B', updated: 1, usage: {} }], active_id: 's2' });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.switchSession('s2'); });
    expect(api.activateSession).toHaveBeenCalledWith('s2');
    expect(result.current.activeSessionId).toBe('s2');
    expect(result.current.summary.components[0].name).toBe('X');
    expect(result.current.transcript.at(-1).text).toBe('switched');
    expect(result.current.canUndo).toBe(true);
    expect(result.current.usage.model).toBe('m-y');
  });

  it('newSession creates a blank slot and refreshes the list', async () => {
    api.createSession.mockResolvedValue({ id: 's3', summary: { components: [], knowledge_bases: [] },
      findings: [], transcript: [], proposal: null, can_undo: false, can_redo: false,
      usage: { input_tokens: 0, output_tokens: 0, turns: 0, model: null } });
    api.listSessions.mockResolvedValue({ sessions: [{ id: 's3', name: 'New session', updated: 9, usage: {} }], active_id: 's3' });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.newSession(); });
    expect(api.createSession).toHaveBeenCalled();
    expect(result.current.activeSessionId).toBe('s3');
    expect(result.current.summary).not.toBeNull();
    await waitFor(() => expect(result.current.sessions.some((x) => x.id === 's3')).toBe(true));
  });

  it('deleteSession activates the backend-returned new active', async () => {
    api.deleteSession.mockResolvedValue({ ok: true, active: 's1' });
    api.activateSession.mockResolvedValue({ id: 's1', summary: { components: [], knowledge_bases: [] },
      findings: [], transcript: [], proposal: null, can_undo: false, can_redo: false,
      usage: { input_tokens: 0, output_tokens: 0, turns: 0, model: null } });
    api.listSessions.mockResolvedValue({ sessions: [{ id: 's1', name: 'A', updated: 1, usage: {} }], active_id: 's1' });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.deleteSession('s2'); });
    expect(api.deleteSession).toHaveBeenCalledWith('s2');
    await waitFor(() => expect(result.current.activeSessionId).toBe('s1'));
  });

  it('renameSession patches then refreshes the list', async () => {
    api.renameSession.mockResolvedValue({ ok: true });
    api.listSessions.mockResolvedValue({ sessions: [{ id: 's1', name: 'Renamed', updated: 1, usage: {} }], active_id: 's1' });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.renameSession('s1', 'Renamed'); });
    expect(api.renameSession).toHaveBeenCalledWith('s1', 'Renamed');
    await waitFor(() => expect(result.current.sessions[0].name).toBe('Renamed'));
  });

  it('a usage SSE event updates usage', async () => {
    api.getSession.mockResolvedValue({ id: 's1', summary: { components: [], knowledge_bases: [] },
      findings: [], transcript: [], proposal: null, can_undo: false, can_redo: false,
      usage: { input_tokens: 0, output_tokens: 0, turns: 0, model: null } });
    api.listSessions.mockResolvedValue({ sessions: [{ id: 's1', name: 'A', updated: 1, usage: {} }], active_id: 's1' });
    api.streamChat.mockImplementation(async (_m, { onEvent }) => {
      onEvent({ type: 'usage', input_tokens: 20, output_tokens: 8, turns: 3, model: 'm-z' });
      onEvent({ type: 'done', canceled: false, text: 'ok' });
    });
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.summary).not.toBeNull());
    await act(async () => { await result.current.send('hi'); });
    await waitFor(() => expect(result.current.usage).toEqual({ input_tokens: 20, output_tokens: 8, turns: 3, model: 'm-z' }));
  });
});
