import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';

beforeEach(() => { vi.restoreAllMocks(); });

describe('api credentials', () => {
  it('axios is configured to send credentials', async () => {
    await import('./api');
    expect(axios.defaults.withCredentials).toBe(true);
  });

  it('streamChat fetch includes credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => ({ read: () => Promise.resolve({ done: true, value: undefined }) }) },
    });
    vi.stubGlobal('fetch', fetchMock);
    const { streamChat } = await import('./api');
    await streamChat('hi', { onEvent: () => {} });
    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][1].credentials).toBe('include');
  });
});
