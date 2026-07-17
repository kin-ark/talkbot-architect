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

  it('dispatches a retry status onto the streaming bubble, cleared on next token', async () => {
    scriptStream([
      { type: 'status', kind: 'retrying', attempt: 1, attempts: 3, wait: 1.0 },
      { type: 'token', delta: 'ok' },
      { type: 'done', canceled: false, text: 'ok' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('hi'); });
    await waitFor(() => {
      const agent = result.current.transcript.filter((m) => m.role === 'agent').at(-1);
      expect(agent.text).toBe('ok');
      expect(agent.status).toBeNull(); // token cleared the retry status
    });
  });

  it('stores the tool result on the trace entry', async () => {
    scriptStream([
      { type: 'tool_start', name: 'validate', args: { x: 1 } },
      { type: 'tool_result', name: 'validate', result: { findings: ['a'] }, summary: '1 finding' },
      { type: 'done', canceled: false, text: 'done' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('check'); });
    await waitFor(() => {
      const agent = result.current.transcript.filter((m) => m.role === 'agent').at(-1);
      const entry = agent.tool_trace.at(-1);
      expect(entry.result).toEqual({ findings: ['a'] });
      expect(entry.summary).toBe('1 finding');
      expect(entry.status).toBe('done');
    });
  });

  it('appends a phase marker into the tool trace', async () => {
    scriptStream([
      { type: 'phase', phase: 'fixing', round: 1, errors: 2, blockers: 0, ts: 1 },
      { type: 'done', canceled: false, text: 'ok', stop_reason: 'complete' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('go'); });
    await waitFor(() => {
      const agent = result.current.transcript.filter((m) => m.role === 'agent').at(-1);
      const phase = agent.tool_trace.find((t) => t._kind === 'phase');
      expect(phase).toMatchObject({ phase: 'fixing', round: 1, errors: 2 });
    });
  });

  it('matches tool_result to tool_start by call_id', async () => {
    scriptStream([
      { type: 'tool_start', name: 'validate', args: {}, call_id: 'a', ts: 1 },
      { type: 'tool_start', name: 'summarize', args: {}, call_id: 'b', ts: 2 },
      { type: 'tool_result', name: 'validate', result: { ok: 1 }, summary: 'done', call_id: 'a', ts: 3 },
      { type: 'done', canceled: false, text: 'x', stop_reason: 'complete' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('go'); });
    await waitFor(() => {
      const agent = result.current.transcript.filter((m) => m.role === 'agent').at(-1);
      const a = agent.tool_trace.find((t) => t.call_id === 'a');
      const b = agent.tool_trace.find((t) => t.call_id === 'b');
      expect(a.status).toBe('done'); expect(a.endTs).toBe(3);
      expect(b.status).toBe('running'); // still running, not overwritten
    });
  });

  it('stores kind + recovery on an error entry and stop_reason on the agent entry', async () => {
    scriptStream([
      { type: 'error', kind: 'proposal_blocked', recovery: ['fix', 'discard'], message: 'blocked' },
      { type: 'done', canceled: false, text: '', stop_reason: 'complete' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('go'); });
    await waitFor(() => {
      const err = result.current.transcript.filter((m) => m.role === 'error').at(-1);
      expect(err).toMatchObject({ kind: 'proposal_blocked', recovery: ['fix', 'discard'] });
    });
  });

  it('stores stop_reason=limit on the agent entry', async () => {
    scriptStream([
      { type: 'token', delta: 'partial' },
      { type: 'done', canceled: false, text: 'partial', stop_reason: 'limit' },
    ]);
    const { result } = renderHook(() => useSession());
    await act(async () => { await result.current.send('go'); });
    await waitFor(() => {
      const agent = result.current.transcript.filter((m) => m.role === 'agent').at(-1);
      expect(agent.stop_reason).toBe('limit');
    });
  });
});
