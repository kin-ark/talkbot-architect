import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import * as store from '../toast/toastStore';
import { useSession } from './useSession';

beforeEach(() => {
  vi.clearAllMocks();
  api.getSession.mockResolvedValue({ summary: null });
  api.listSessions.mockResolvedValue({ sessions: [], active_id: null });
});

describe('useSession toasts', () => {
  it('fires an error toast when an action fails', async () => {
    const spy = vi.spyOn(store.toast, 'error');
    api.setSpeechName.mockRejectedValue(new Error('boom'));
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.renameBot('X'); });
    expect(spy).toHaveBeenCalled();
  });

  it('fires a success toast on rename', async () => {
    const spy = vi.spyOn(store.toast, 'success');
    api.setSpeechName.mockResolvedValue({ summary: {}, findings: [], can_undo: true, can_redo: false, bot_name: 'X' });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.renameBot('X'); });
    expect(spy).toHaveBeenCalledWith('Renamed to X');
  });
});
