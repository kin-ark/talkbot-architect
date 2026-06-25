import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import { useSession } from './useSession';

beforeEach(() => vi.clearAllMocks());

function scriptStream(events) {
  api.streamChat.mockImplementation(async (_msg, { onEvent }) => {
    for (const e of events) onEvent(e);
  });
}

describe('useSession streaming', () => {
  it('accumulates token deltas into one agent message', async () => {
    scriptStream([
      { type: 'token', delta: 'Hel' }, { type: 'token', delta: 'lo' },
      { type: 'done', canceled: false, text: 'Hello' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('hi'); });
    await waitFor(() => {
      const agent = result.current.transcript.filter((m) => m.role === 'agent');
      expect(agent[agent.length - 1].text).toBe('Hello');
    });
    expect(result.current.sending).toBe(false);
  });

  it('records tool trace + proposal', async () => {
    scriptStream([
      { type: 'tool_start', name: 'validate', args: {} },
      { type: 'tool_result', name: 'validate', result: {}, summary: '0 findings' },
      { type: 'proposal', proposal: { diff: 'x', checker_delta: null } },
      { type: 'done', canceled: false, text: 'done' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('check'); });
    await waitFor(() => expect(result.current.proposal).toEqual({ diff: 'x', checker_delta: null }));
    const agent = result.current.transcript.filter((m) => m.role === 'agent').at(-1);
    expect(agent.tool_trace.map((t) => t.name)).toContain('validate');
  });

  it('appends an error bubble on an error event', async () => {
    scriptStream([
      { type: 'error', message: 'boom' },
      { type: 'done', canceled: false, text: '' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('hi'); });
    await waitFor(() => {
      const errs = result.current.transcript.filter((m) => m.role === 'error');
      expect(errs.at(-1).text).toContain('boom');
    });
  });
});
