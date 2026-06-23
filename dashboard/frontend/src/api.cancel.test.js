import { vi, describe, it, expect, beforeEach } from 'vitest';
import axios from 'axios';
vi.mock('axios');

import { sendChat, cancelChat } from './api';

describe('api cancel', () => {
  beforeEach(() => vi.clearAllMocks());

  it('sendChat forwards an abort signal', async () => {
    axios.post.mockResolvedValue({ data: {} });
    const ctrl = new AbortController();
    await sendChat('hi', ctrl.signal);
    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/chat'),
      { message: 'hi' },
      expect.objectContaining({ signal: ctrl.signal }),
    );
  });

  it('cancelChat posts to /chat/cancel', async () => {
    axios.post.mockResolvedValue({ data: { canceling: true } });
    await cancelChat();
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/chat/cancel'));
  });
});
