/**
 * Tests for api.js BASE resolution.
 *
 * Approach: `BASE` is a module-level constant evaluated at import time, so
 * vi.stubEnv alone is not enough — the module must be re-imported after each
 * stub. We use vi.resetModules() before each test so the dynamic import gets a
 * fresh evaluation of import.meta.env.VITE_API_URL.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('apiBase() — VITE_API_URL resolution', () => {
  it('returns empty string (same-origin) when VITE_API_URL is empty string', async () => {
    vi.stubEnv('VITE_API_URL', '');
    const { apiBase } = await import('./api.js');
    expect(apiBase()).toBe('');
  });

  it('returns localhost fallback when VITE_API_URL is undefined (dev)', async () => {
    vi.stubEnv('VITE_API_URL', undefined);
    const { apiBase } = await import('./api.js');
    expect(apiBase()).toBe('http://localhost:8000');
  });

  it('returns the absolute URL when VITE_API_URL is set to a real host', async () => {
    vi.stubEnv('VITE_API_URL', 'https://example.com');
    const { apiBase } = await import('./api.js');
    expect(apiBase()).toBe('https://example.com');
  });
});
