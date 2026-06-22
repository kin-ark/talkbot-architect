import { useState, useCallback } from 'react';
import * as api from '../api';

export function useSession() {
  const [summary, setSummary] = useState(null);
  const [findings, setFindings] = useState([]);
  const [transcript, setTranscript] = useState([]);
  const [proposal, setProposal] = useState(null);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [loading, setLoading] = useState(false);

  const upload = useCallback(async (file) => {
    setLoading(true);
    try {
      const r = await api.uploadSession(file);
      setSummary(r.summary); setFindings(r.findings);
      setTranscript([{ role: 'agent', text: `Loaded. ${r.findings.filter(f => f.severity === 'error').length} errors, ${r.findings.filter(f => f.severity === 'warning').length} warnings. What do you want to do?` }]);
    } finally { setLoading(false); }
  }, []);

  const send = useCallback(async (message) => {
    setTranscript((t) => [...t, { role: 'user', text: message }]);
    const r = await api.sendChat(message);
    setTranscript((t) => [...t, { role: 'agent', text: r.text, tool_trace: r.tool_trace }]);
    setProposal(r.proposal || null);
  }, []);

  const refresh = (r) => {
    setSummary(r.summary); setFindings(r.findings);
    setCanUndo(r.can_undo); setCanRedo(r.can_redo); setProposal(null);
  };
  const apply = useCallback(async () => refresh(await api.applyPending()), []);
  const reject = useCallback(() => setProposal(null), []);
  const undo = useCallback(async () => refresh(await api.undo()), []);
  const redo = useCallback(async () => refresh(await api.redo()), []);

  return { summary, findings, transcript, proposal, canUndo, canRedo, loading,
           upload, send, apply, reject, undo, redo };
}
