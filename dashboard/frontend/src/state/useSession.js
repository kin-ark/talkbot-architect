import { useState, useCallback, useRef } from 'react';
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

  const queue = useRef([]);
  const draining = useRef(false);
  const ctrl = useRef(null);

  const upload = useCallback(async (file) => {
    setLoading(true);
    try {
      const r = await api.uploadSession(file);
      setSummary(r.summary); setFindings(r.findings);
      setTranscript([{ role: 'agent', text: `Loaded. ${r.findings.filter(f => f.severity === 'error').length} errors, ${r.findings.filter(f => f.severity === 'warning').length} warnings. What do you want to do?` }]);
    } finally { setLoading(false); }
  }, []);

  const startBlank = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.startBlank();
      setSummary(r.summary); setFindings(r.findings);
      setTranscript([{ role: 'agent', text: "Blank canvas. Describe the bot you want — e.g. \"make me a Debt Collector talkbot\"." }]);
    } finally { setLoading(false); }
  }, []);

  const errText = (e) =>
    e?.response?.data?.detail
    || e?.response?.data?.error?.message
    || (e?.response?.status === 503 ? 'No AI key configured — open ⚙ to set a provider and key.' : null)
    || e?.message || 'Request failed.';

  const drain = useCallback(async () => {
    if (draining.current) return;
    draining.current = true;
    setSending(true);
    try {
      while (queue.current.length) {
        const msg = queue.current.shift();
        ctrl.current = new AbortController();
        // placeholder agent bubble this turn fills
        let agentIdx = -1;
        setTranscript((t) => { agentIdx = t.length; return [...t, { role: 'agent', text: '', tool_trace: [] }]; });
        const patch = (fn) => setTranscript((t) => t.map((m, i) => (i === agentIdx ? fn(m) : m)));
        try {
          await api.streamChat(msg, {
            signal: ctrl.current.signal,
            onEvent: (e) => {
              if (e.type === 'token') patch((m) => ({ ...m, text: m.text + e.delta }));
              else if (e.type === 'tool_start') patch((m) => ({ ...m, tool_trace: [...m.tool_trace, { name: e.name, arguments: e.args, status: 'running' }] }));
              else if (e.type === 'tool_result') patch((m) => ({ ...m, tool_trace: m.tool_trace.map((tt, i) => (i === m.tool_trace.length - 1 ? { ...tt, status: 'done', summary: e.summary } : tt)) }));
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
    }
  }, []);

  const send = useCallback(async (message) => {
    setTranscript((t) => [...t, { role: 'user', text: message }]);
    queue.current.push(message);
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

  return { summary, findings, transcript, proposal, canUndo, canRedo, loading, sending,
           upload, startBlank, send, apply, reject, undo, redo, cancel };
}
