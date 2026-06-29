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

describe('useSession loadSample', () => {
  it('loads a sample into the workspace', async () => {
    api.loadSample.mockResolvedValue({
      summary: { components: [{ uuid: 'c', name: 'Greeting & FAQ', nodes: {} }], knowledge_bases: [] },
      findings: [],
    });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.loadSample('greeting_faq'); });
    expect(api.loadSample).toHaveBeenCalledWith('greeting_faq');
    expect(result.current.summary.components[0].name).toBe('Greeting & FAQ');
    await waitFor(() => expect(api.listSessions).toHaveBeenCalled());
  });
});
