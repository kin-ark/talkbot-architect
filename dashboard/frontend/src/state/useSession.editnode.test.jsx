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

describe('useSession editNodeText', () => {
  it('calls the api and refreshes summary + undo state', async () => {
    api.editNodeText.mockResolvedValue({
      ok: true,
      summary: { components: [{ uuid: 'c', name: 'X', nodes: { n1: { label: 'New', text: 't' } } }], knowledge_bases: [] },
      findings: [], can_undo: true, can_redo: false,
    });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.editNodeText('n1', { label: 'New' }); });
    expect(api.editNodeText).toHaveBeenCalledWith('n1', { label: 'New' });
    await waitFor(() => expect(result.current.canUndo).toBe(true));
    expect(result.current.summary.components[0].nodes.n1.label).toBe('New');
  });
});
