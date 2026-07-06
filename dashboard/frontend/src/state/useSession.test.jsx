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

  it('upload with is_component response sets isComponent to true', async () => {
    api.uploadSession.mockResolvedValue({
      summary: { components: [] },
      findings: [],
      is_component: true,
      component_warnings: ['KB not allowed in component'],
    });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.upload(new File(['{}'], 'c.json')); });
    expect(result.current.isComponent).toBe(true);
    expect(result.current.componentWarnings).toEqual(['KB not allowed in component']);
  });

  it('startBlank resets isComponent to false', async () => {
    api.startBlank.mockResolvedValue({ summary: { components: [] }, findings: [] });
    const { result } = renderHook(() => useSession());
    // Start in a component state
    await act(async () => {
      result.current.upload = vi.fn(async () => {
        expect(result.current.isComponent).toBe(false);
      });
    });
    await act(async () => { await result.current.startBlank(); });
    expect(result.current.isComponent).toBe(false);
    expect(result.current.componentWarnings).toEqual([]);
  });

  it('loadSample resets isComponent to false', async () => {
    api.loadSample.mockResolvedValue({
      summary: { components: [{ name: 'Sample' }] },
      findings: [],
    });
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.loadSample('sample-id'); });
    expect(result.current.isComponent).toBe(false);
    expect(result.current.componentWarnings).toEqual([]);
  });

  it('reset clears isComponent', async () => {
    api.clearSession.mockResolvedValue({});
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.reset(); });
    expect(result.current.isComponent).toBe(false);
    expect(result.current.componentWarnings).toEqual([]);
  });

  it('startNew clears isComponent', async () => {
    const { result } = renderHook(() => useSession());
    await act(async () => { result.current.startNew(); });
    expect(result.current.isComponent).toBe(false);
    expect(result.current.componentWarnings).toEqual([]);
  });
});
