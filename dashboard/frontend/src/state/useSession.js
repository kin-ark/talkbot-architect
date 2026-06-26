import { useState, useCallback, useRef, useEffect } from 'react';
import * as api from '../api';

export function useSession() {
  const [summary, setSummary] = useState(null);
  const [findings, setFindings] = useState([]);
  const [transcript, setTranscript] = useState([]);
  const [proposal, setProposal] = useState(null);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [usage, setUsage] = useState(null);

  const queue = useRef([]);
  const draining = useRef(false);
  const ctrl = useRef(null);
  const turnSeq = useRef(0);
  const touched = useRef(false);
  const lastSent = useRef(null);

  const _applyPayload = useCallback((r) => {
    setSummary(r.summary || null);
    setFindings(r.findings || []);
    setTranscript(r.transcript || []);
    setProposal(r.proposal || null);
    setCanUndo(!!r.can_undo);
    setCanRedo(!!r.can_redo);
    setUsage(r.usage || null);
    if (r.id !== undefined) setActiveSessionId(r.id);
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      const r = await api.listSessions();
      setSessions(r.sessions || []);
      if (r.active_id !== undefined && r.active_id !== null) setActiveSessionId(r.active_id);
      return r;
    } catch { return null; }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.resolve(api.getSession()).then((r) => {
      if (cancelled) return;
      if (!touched.current && r?.summary) {
        setSummary(r.summary);
        setFindings(r.findings || []);
        setTranscript(r.transcript || []);
        setProposal(r.proposal || null);
        setCanUndo(!!r.can_undo);
        setCanRedo(!!r.can_redo);
        setUsage(r.usage || null);
        if (r.id !== undefined) setActiveSessionId(r.id);
      }
      if (!cancelled) refreshSessions();
    }).catch(() => { if (!cancelled) refreshSessions(); });
    return () => { cancelled = true; };
  }, [refreshSessions]);

  const upload = useCallback(async (file) => {
    touched.current = true;
    setLoading(true);
    try {
      const r = await api.uploadSession(file);
      setSummary(r.summary); setFindings(r.findings);
      setTranscript([{ role: 'agent', text: `Loaded. ${r.findings.filter(f => f.severity === 'error').length} errors, ${r.findings.filter(f => f.severity === 'warning').length} warnings. What do you want to do?` }]);
      await refreshSessions();
    } finally { setLoading(false); }
  }, [refreshSessions]);

  const startBlank = useCallback(async () => {
    touched.current = true;
    setLoading(true);
    try {
      const r = await api.startBlank();
      setSummary(r.summary); setFindings(r.findings);
      setTranscript([{ role: 'agent', text: "Blank canvas. Describe the bot you want — e.g. \"make me a Debt Collector talkbot\"." }]);
      await refreshSessions();
    } finally { setLoading(false); }
  }, [refreshSessions]);

  const switchSession = useCallback(async (id) => {
    touched.current = true;
    queue.current = [];
    if (ctrl.current) ctrl.current.abort();
    const r = await api.activateSession(id);
    _applyPayload(r);
    await refreshSessions();
  }, [_applyPayload, refreshSessions]);

  const newSession = useCallback(async () => {
    touched.current = true;
    queue.current = [];
    if (ctrl.current) ctrl.current.abort();
    const r = await api.createSession();
    _applyPayload(r);
    setTranscript([{ role: 'agent', text: "Blank canvas. Describe the bot you want — e.g. \"make me a Debt Collector talkbot\"." }]);
    await refreshSessions();
  }, [_applyPayload, refreshSessions]);

  const renameSession = useCallback(async (id, name) => {
    await api.renameSession(id, name);
    await refreshSessions();
  }, [refreshSessions]);

  const deleteSession = useCallback(async (id) => {
    const r = await api.deleteSession(id);
    if (id === activeSessionId && r?.active) {
      await switchSession(r.active);
    } else if (id === activeSessionId && !r?.active) {
      // deleted the only session → blank landing
      setSummary(null); setFindings([]); setTranscript([]); setProposal(null);
      setCanUndo(false); setCanRedo(false); setUsage(null); setActiveSessionId(null);
    }
    await refreshSessions();
  }, [activeSessionId, switchSession, refreshSessions]);

  const errText = (e) =>
    e?.response?.data?.detail
    || e?.response?.data?.error?.message
    || (e?.response?.status === 503 ? 'No AI key configured — open Settings to set a provider and key.' : null)
    || e?.message || 'Request failed.';

  const drain = useCallback(async () => {
    if (draining.current) return;
    draining.current = true;
    setSending(true);
    try {
      while (queue.current.length) {
        const msg = queue.current.shift();
        ctrl.current = new AbortController();
        // placeholder agent bubble this turn fills. Patch by a stable id (NOT
        // array index): the id is assigned before setTranscript, so the closure
        // is correct even when SSE events arrive async across render batches.
        const aid = `a${turnSeq.current++}`;
        setTranscript((t) => [...t, { role: 'agent', text: '', tool_trace: [], _id: aid }]);
        const patch = (fn) => setTranscript((t) => t.map((m) => (m._id === aid ? fn(m) : m)));
        try {
          await api.streamChat(msg, {
            signal: ctrl.current.signal,
            onEvent: (e) => {
              if (e.type === 'token') patch((m) => ({ ...m, text: m.text + e.delta }));
              else if (e.type === 'tool_start') patch((m) => ({ ...m, tool_trace: [...m.tool_trace, { name: e.name, arguments: e.args, status: 'running' }] }));
              else if (e.type === 'tool_result') patch((m) => ({ ...m, tool_trace: m.tool_trace.map((tt, i) => (i === m.tool_trace.length - 1 ? { ...tt, status: 'done', summary: e.summary } : tt)) }));
              else if (e.type === 'usage') setUsage({ input_tokens: e.input_tokens, output_tokens: e.output_tokens, turns: e.turns, model: e.model });
              else if (e.type === 'proposal') setProposal(e.proposal);
              else if (e.type === 'error') setTranscript((t) => [...t, { role: 'error', text: e.message }]);
              else if (e.type === 'done' && e.text) patch((m) => ({ ...m, text: e.text }));
            },
          });
        } catch (e) {
          queue.current = [];
          if (e?.name !== 'AbortError' && e?.name !== 'CanceledError') {
            setTranscript((t) => [...t, { role: 'error', text: errText(e) }]);
          }
        }
      }
    } finally {
      draining.current = false;
      setSending(false);
      ctrl.current = null;
      refreshSessions();
    }
  }, [refreshSessions]);

  const send = useCallback(async (message) => {
    touched.current = true;
    lastSent.current = message;
    setTranscript((t) => [...t, { role: 'user', text: message }]);
    queue.current.push(message);
    await drain();
  }, [drain]);

  const retry = useCallback(async () => {
    if (!lastSent.current) return;
    const msg = lastSent.current;
    setTranscript((t) => [...t, { role: 'user', text: msg }]);
    queue.current.push(msg);
    await drain();
  }, [drain]);

  const cancel = useCallback(() => {
    queue.current = [];
    if (ctrl.current) ctrl.current.abort();
    api.cancelChat().catch(() => {});
  }, []);

  const refresh = (r) => {
    setSummary(r.summary); setFindings(r.findings);
    setCanUndo(r.can_undo); setCanRedo(r.can_redo); setProposal(null);
  };
  const apply = useCallback(async () => refresh(await api.applyPending()), []);
  const reject = useCallback(() => setProposal(null), []);
  const undo = useCallback(async () => refresh(await api.undo()), []);
  const redo = useCallback(async () => refresh(await api.redo()), []);

  // Clear backend + local state so the app returns to the upload/landing screen.
  // Without clearing the backend, a later reload would rehydrate the old session.
  const reset = useCallback(async () => {
    queue.current = [];
    if (ctrl.current) ctrl.current.abort();
    try { await api.clearSession(); } catch { /* best-effort */ }
    setSummary(null); setFindings([]); setTranscript([]); setProposal(null);
    setCanUndo(false); setCanRedo(false); setUsage(null); setActiveSessionId(null);
    await refreshSessions();
  }, [refreshSessions]);

  return { summary, findings, transcript, proposal, canUndo, canRedo, loading, sending,
           sessions, activeSessionId, usage,
           upload, startBlank, send, retry, apply, reject, undo, redo, cancel, reset,
           refreshSessions, newSession, switchSession, renameSession, deleteSession };
}
