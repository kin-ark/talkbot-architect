import { vi, describe, it, expect } from 'vitest';
vi.mock('axios');
import axios from 'axios';
import { sendChat } from './api';

describe('api', () => {
  it('sendChat posts message to /chat', async () => {
    axios.post.mockResolvedValue({ data: { text: 'hi', tool_trace: [], proposal: null } });
    const r = await sendChat('hello');
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/chat'), { message: 'hello' }, expect.objectContaining({}));
    expect(r.text).toBe('hi');
  });
});
