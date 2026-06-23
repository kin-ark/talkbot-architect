import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

describe('useSession queue + errors', () => {
  beforeEach(() => vi.clearAllMocks());

  it('appends an error bubble when a turn fails', async () => {
    api.sendChat.mockRejectedValue({ response: { data: { detail: 'LLM provider error: boom' } } });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('hi'); });
    await waitFor(() => {
      const errs = result.current.transcript.filter((m) => m.role === 'error');
      expect(errs.length).toBe(1);
      expect(errs[0].text).toContain('boom');
    });
    expect(result.current.sending).toBe(false);
  });

  it('exposes a cancel that calls the API', async () => {
    api.cancelChat.mockResolvedValue({ canceling: true });
    const { result } = renderHook(() => useSession());
    act(() => { result.current.cancel(); });
    expect(api.cancelChat).toHaveBeenCalled();
  });
});
