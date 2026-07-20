import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { uploadSession } from './api';

vi.mock('axios');

describe('uploadSession progress', () => {
  beforeEach(() => vi.resetAllMocks());

  it('maps axios loaded/total to an integer pct', async () => {
    let captured;
    axios.post.mockImplementation((_url, _fd, cfg) => { captured = cfg.onUploadProgress; return Promise.resolve({ data: { ok: 1 } }); });
    const seen = [];
    await uploadSession(new File(['x'], 's.json'), (p) => seen.push(p));
    captured({ loaded: 50, total: 200 });
    captured({ loaded: 200, total: 200 });
    expect(seen).toEqual([25, 100]);
  });

  it('reports null when total is missing', async () => {
    let captured;
    axios.post.mockImplementation((_url, _fd, cfg) => { captured = cfg.onUploadProgress; return Promise.resolve({ data: {} }); });
    const seen = [];
    await uploadSession(new File(['x'], 's.json'), (p) => seen.push(p));
    captured({ loaded: 10, total: 0 });
    expect(seen).toEqual([null]);
  });

  it('works without a callback', async () => {
    axios.post.mockResolvedValue({ data: { ok: 1 } });
    await expect(uploadSession(new File(['x'], 's.json'))).resolves.toEqual({ ok: 1 });
  });
});
