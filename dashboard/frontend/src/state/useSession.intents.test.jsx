import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => {
  vi.clearAllMocks();
  api.getSession.mockResolvedValue({ summary: { components: [], knowledge_bases: [] }, findings: [] });
  api.listSessions.mockResolvedValue({ sessions: [], active_id: null });
  api.listIntents.mockResolvedValue([{ id: '1', name: 'X', type: 'user', keyword_count: 1, response_count: 0, needs_nlu: false }]);
});

describe('useSession intents', () => {
  it('loads intents on mount when a doc is present', async () => {
    const { result } = renderHook(() => useSession());
    await waitFor(() => expect(result.current.intents.map((i) => i.name)).toContain('X'));
  });
});
