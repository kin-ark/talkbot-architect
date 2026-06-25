import { vi, describe, it, expect, beforeEach } from 'vitest';
import axios from 'axios';
vi.mock('axios');

import { cancelChat } from './api';

describe('api cancel', () => {
  beforeEach(() => vi.clearAllMocks());

  it('cancelChat posts to /chat/cancel', async () => {
    axios.post.mockResolvedValue({ data: { canceling: true } });
    await cancelChat();
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/chat/cancel'));
  });
});
