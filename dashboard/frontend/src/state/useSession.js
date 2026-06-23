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
        try {
          const r = await api.sendChat(msg, ctrl.current.signal);
          setTranscript((t) => [...t, { role: 'agent', text: r.text, tool_trace: r.tool_trace }]);
          setProposal(r.proposal || null);
        } catch (e) {
          queue.current = [];        // halt the queue on error/cancel
          if (e?.code !== 'ERR_CANCELED' && e?.name !== 'CanceledError') {
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
           upload, send, apply, reject, undo, redo, cancel };
}
