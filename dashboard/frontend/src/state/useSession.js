import { useState, useCallback, useRef, useEffect } from 'react';
import * as api from '../api';
import { toast } from '../toast/toastStore';

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
  const [botName, setBotName] = useState(null);
  const [intents, setIntents] = useState([]);
  const [isComponent, setIsComponent] = useState(false);
  const [componentWarnings, setComponentWarnings] = useState([]);

  const queue = useRef([]);
  const draining = useRef(false);
  const ctrl = useRef(null);
  const turnSeq = useRef(0);
  const touched = useRef(false);
  const lastSent = useRef(null);
  const urlsRef = useRef(new Set());

  const _applyPayload = useCallback((r) => {
    setSummary(r.summary || null);
    setFindings(r.findings || []);
    setTranscript(r.transcript || []);
    setProposal(r.proposal || null);
    setCanUndo(!!r.can_undo);
    setCanRedo(!!r.can_redo);
    setUsage(r.usage || null);
    setBotName(r.bot_name ?? null);
    setIsComponent(Boolean(r.is_component));
    setComponentWarnings(r.component_warnings || []);
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

  const refreshIntents = useCallback(async () => {
    try { setIntents(await api.listIntents()); } catch { setIntents([]); }
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
        setBotName(r.bot_name ?? null);
        setIsComponent(Boolean(r.is_component));
        setComponentWarnings(r.component_warnings || []);
        if (r.id !== undefined) setActiveSessionId(r.id);
        refreshIntents();
      }
      if (!cancelled) refreshSessions();
    }).catch(() => { if (!cancelled) refreshSessions(); });
    return () => { cancelled = true; };
  }, [refreshSessions, refreshIntents]);

  useEffect(() => () => { urlsRef.current.forEach((u) => URL.revokeObjectURL(u)); }, []);

  const _revokeUrls = () => { urlsRef.current.forEach((u) => URL.revokeObjectURL(u)); urlsRef.current.clear(); };

  const errText = (e) =>
    e?.response?.data?.detail
    || e?.response?.data?.error?.message
    || (e?.response?.status === 503 ? 'No AI key configured — open Settings to set a provider and key.' : null)
    || e?.message || 'Request failed.';

  const upload = useCallback(async (file) => {
    touched.current = true;
    setLoading(true);
    try {
      const r = await api.uploadSession(file);
      setSummary(r.summary); setFindings(r.findings);
      setIsComponent(Boolean(r.is_component));
      setComponentWarnings(r.component_warnings || []);
      setTranscript([{ role: 'agent', text: `Loaded. ${r.findings.filter(f => f.severity === 'error').length} errors, ${r.findings.filter(f => f.severity === 'warning').length} warnings. What do you want to do?` }]);
      await refreshSessions();
      await refreshIntents();
    } catch (e) { toast.error(errText(e)); } finally { setLoading(false); }
  }, [refreshSessions, refreshIntents]);

  const startBlank = useCallback(async () => {
    touched.current = true;
    setLoading(true);
    try {
      const r = await api.startBlank();
      setSummary(r.summary); setFindings(r.findings);
      setIsComponent(false);
      setComponentWarnings([]);
      setTranscript([{ role: 'agent', text: "Blank canvas. Describe the bot you want — e.g. \"make me a Debt Collector talkbot\"." }]);
      await refreshSessions();
      await refreshIntents();
    } catch (e) { toast.error(errText(e)); } finally { setLoading(false); }
  }, [refreshSessions, refreshIntents]);

  const loadSample = useCallback(async (id) => {
    touched.current = true;
    setLoading(true);
    try {
      const r = await api.loadSample(id);
      setSummary(r.summary); setFindings(r.findings);
      setIsComponent(false);
      setComponentWarnings([]);
      setTranscript([{ role: 'agent', text: `Loaded the ${r.summary?.components?.[0]?.name || 'sample'} sample — explore the graph, or ask me to change it.` }]);
      await refreshSessions();
      await refreshIntents();
    } catch (e) { toast.error(errText(e)); } finally { setLoading(false); }
  }, [refreshSessions, refreshIntents]);

  const switchSession = useCallback(async (id) => {
    try {
      touched.current = true;
      queue.current = [];
      if (ctrl.current) ctrl.current.abort();
      _revokeUrls();   // switched-away bubble attachments are frontend-only + never rehydrated
      const r = await api.activateSession(id);
      _applyPayload(r);
      await refreshSessions();
      await refreshIntents();
    } catch (e) { toast.error(errText(e)); }
  }, [_applyPayload, refreshSessions, refreshIntents]);

  const newSession = useCallback(async () => {
    touched.current = true;
    queue.current = [];
    if (ctrl.current) ctrl.current.abort();
    _revokeUrls();
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
    try {
      const r = await api.deleteSession(id);
      if (id === activeSessionId && r?.active) {
        await switchSession(r.active);   // already calls refreshSessions; no need to repeat
        toast.success('Session deleted');
        return;
      } else if (id === activeSessionId && !r?.active) {
        // deleted the only session → blank landing
        _revokeUrls();
        setSummary(null); setFindings([]); setTranscript([]); setProposal(null);
        setCanUndo(false); setCanRedo(false); setUsage(null); setActiveSessionId(null);
      }
      await refreshSessions();
      toast.success('Session deleted');
    } catch (e) { toast.error(errText(e)); }
  }, [activeSessionId, switchSession, refreshSessions]);

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
        setTranscript((t) => [...t, { role: 'agent', text: '', tool_trace: [], reasoning: '', _id: aid }]);
        const patch = (fn) => setTranscript((t) => t.map((m) => (m._id === aid ? fn(m) : m)));
        try {
          await api.streamChat(msg, {
            signal: ctrl.current.signal,
            onEvent: (e) => {
              if (e.type === 'status') patch((m) => ({ ...m, status: e }));
              else if (e.type === 'thinking') patch((m) => ({ ...m, status: null, reasoning: (m.reasoning || '') + e.delta }));
              else if (e.type === 'token') patch((m) => ({ ...m, status: null, text: m.text + e.delta }));
              else if (e.type === 'phase') patch((m) => ({ ...m, tool_trace: [...m.tool_trace, { _kind: 'phase', phase: e.phase, round: e.round, errors: e.errors, blockers: e.blockers, ts: e.ts }] }));
              else if (e.type === 'tool_start') patch((m) => ({ ...m, tool_trace: [...m.tool_trace, { _kind: 'tool', call_id: e.call_id, name: e.name, arguments: e.args, ts: e.ts, status: 'running' }] }));
              else if (e.type === 'tool_result') patch((m) => ({ ...m, tool_trace: m.tool_trace.map((tt) => (tt._kind === 'tool' && tt.call_id === e.call_id ? { ...tt, status: 'done', summary: e.summary, result: e.result, endTs: e.ts } : tt)) }));
              else if (e.type === 'usage') setUsage({ input_tokens: e.input_tokens, output_tokens: e.output_tokens, turns: e.turns, model: e.model });
              else if (e.type === 'proposal') setProposal(e.proposal);
              else if (e.type === 'error') setTranscript((t) => [...t, { role: 'error', text: e.message, kind: e.kind, recovery: e.recovery }]);
              else if (e.type === 'done') { if (e.text) patch((m) => ({ ...m, text: e.text })); if (e.stop_reason) patch((m) => ({ ...m, stop_reason: e.stop_reason })); }
            },
          });
        } catch (e) {
          queue.current = [];
          if (e?.name !== 'AbortError' && e?.name !== 'CanceledError') {
            setTranscript((t) => [...t, { role: 'error', text: errText(e) }]);
            toast.error(errText(e));
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

  const send = useCallback(async (arg) => {
    const payload = typeof arg === 'string' ? { text: arg } : (arg || {});
    const message = payload.text || '';
    const images = payload.images || [];
    const file = payload.attachment || null;
    touched.current = true;
    lastSent.current = message;
    setTranscript((t) => [...t, { role: 'user', text: message, images, file }]);
    images.forEach((im) => im?.url && urlsRef.current.add(im.url));
    if (file?.url) urlsRef.current.add(file.url);
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
    refreshIntents();
  };
  const apply = useCallback(async () => {
    try {
      const r = await api.applyPending();
      refresh(r);
      if (r.bot_name !== undefined) setBotName(r.bot_name ?? null);
      refreshSessions();
      toast.success('Change applied');
    } catch (e) { toast.error(errText(e)); }
  }, [refreshSessions]);
  const reject = useCallback(() => setProposal(null), []);
  const undo = useCallback(async () => {
    try {
      const r = await api.undo();
      refresh(r);
      if (r.bot_name !== undefined) setBotName(r.bot_name ?? null);
      refreshSessions();
    } catch (e) { toast.error(errText(e)); }
  }, [refreshSessions]);
  const redo = useCallback(async () => {
    try {
      const r = await api.redo();
      refresh(r);
      if (r.bot_name !== undefined) setBotName(r.bot_name ?? null);
      refreshSessions();
    } catch (e) { toast.error(errText(e)); }
  }, [refreshSessions]);

  const renameBot = useCallback(async (name) => {
    try {
      const r = await api.setSpeechName(name);
      refresh(r);
      setBotName(r.bot_name ?? null);
      refreshSessions();
      toast.success('Renamed to ' + name);
    } catch (e) { toast.error(errText(e)); }
  }, [refreshSessions]);

  const editNodeText = useCallback(async (uuid, fields) => {
    try {
      const r = await api.editNodeText(uuid, fields);
      refresh(r);   // summary/findings/canUndo/canRedo, clears proposal
      return r;
    } catch (e) { toast.error(errText(e)); }
  }, []);

  // Clear backend + local state so the app returns to the upload/landing screen.
  // Without clearing the backend, a later reload would rehydrate the old session.
  const reset = useCallback(async () => {
    queue.current = [];
    if (ctrl.current) ctrl.current.abort();
    try { await api.clearSession(); } catch { /* best-effort */ }
    _revokeUrls();
    setSummary(null); setFindings([]); setTranscript([]); setProposal(null);
    setCanUndo(false); setCanRedo(false); setUsage(null); setBotName(null); setActiveSessionId(null);
    setIsComponent(false); setComponentWarnings([]);
    await refreshSessions();
  }, [refreshSessions]);

  // Return to the empty-state center WITHOUT clearing the backend or the
  // session list — the user picks a start method (upload/sample/blank) next,
  // and that creates the slot. Contrast reset(), which clears the backend
  // and nulls the active session.
  const startNew = useCallback(() => {
    queue.current = [];
    if (ctrl.current) ctrl.current.abort();
    _revokeUrls();
    setSummary(null); setFindings([]); setTranscript([]); setProposal(null);
    setCanUndo(false); setCanRedo(false); setBotName(null);
    setIsComponent(false); setComponentWarnings([]);
  }, []);

  return { summary, findings, transcript, proposal, canUndo, canRedo, loading, sending,
           sessions, activeSessionId, usage, botName, intents, isComponent, componentWarnings,
           upload, startBlank, loadSample, send, retry, apply, reject, undo, redo, cancel, reset, startNew,
           refreshSessions, refreshIntents, newSession, switchSession, renameSession, deleteSession, renameBot, editNodeText };
}
