import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import * as api from '../api';
import { useSession } from './useSession';

vi.mock('../api');

describe('useSession', () => {
  beforeEach(() => vi.resetAllMocks());
  it('upload populates summary and findings', async () => {
    api.uploadSession.mockResolvedValue({ summary: { components: [] }, findings: [] });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.upload(new File(['{}'], 's.json')); });
    expect(result.current.summary).toEqual({ components: [] });
  });
});
