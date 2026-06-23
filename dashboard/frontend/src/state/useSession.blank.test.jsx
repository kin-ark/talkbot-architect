import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import * as api from '../api';
import { useSession } from './useSession';

vi.mock('../api');

describe('useSession startBlank', () => {
  beforeEach(() => vi.resetAllMocks());
  it('startBlank seeds summary and opener transcript', async () => {
    api.startBlank.mockResolvedValue({ summary: { components: [] }, findings: [] });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.startBlank(); });
    expect(result.current.summary).toEqual({ components: [] });
    expect(result.current.transcript).toHaveLength(1);
    expect(result.current.transcript[0].role).toBe('agent');
  });
});
