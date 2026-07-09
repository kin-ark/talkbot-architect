import { useState, useEffect } from 'react';
import { getConfig, updateConfig, clearConfig, getModels } from '../api';
import Button from './ui/Button';

export default function SettingsPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null);
  const [models, setModels] = useState([]);
  const [modelId, setModelId] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showReasoning, setShowReasoning] = useState(true);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- legitimate async-fetch loader pattern; setLoading/setNotice reset before an async call, not as a derived-state sync
    setLoading(true);
    setNotice(null);
    Promise.all([getModels(), getConfig()])
      .then(([m, cfg]) => {
        if (cancelled) return;
        setModels(m.models);
        setStatus(cfg);
        setModelId(cfg.model_id || m.default);
        setShowReasoning(cfg.show_reasoning !== false);
      })
      .catch(() => { if (!cancelled) setNotice({ type: 'err', text: 'Failed to load config.' }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const handleSave = async () => {
    setNotice(null);
    const payload = { model_id: modelId, show_reasoning: showReasoning };
    if (apiKey) payload.api_key = apiKey;
    try {
      const cfg = await updateConfig(payload);
      setStatus(cfg);
      setApiKey('');
      setNotice({ type: 'ok', text: 'Saved.' });
    } catch {
      setNotice({ type: 'err', text: 'Save failed.' });
    }
  };

  const handleReset = async () => {
    setNotice(null);
    try {
      const cfg = await clearConfig();
      setStatus(cfg);
      setModelId(cfg.model_id || '');
      setShowReasoning(cfg.show_reasoning !== false);
      setApiKey('');
      setNotice({ type: 'ok', text: 'Reset to env defaults.' });
    } catch {
      setNotice({ type: 'err', text: 'Reset failed.' });
    }
  };

  return (
    <div data-testid="settings-page" className="text-sm text-text">
      <p className="font-semibold mb-3">AI settings</p>
      {loading && <p className="text-text-tertiary mb-2">Loading…</p>}
      {status && (
        <p className="mb-3 text-text-secondary text-xs">
          API key:{' '}
          <span className={status.key_set ? 'text-success font-medium' : 'text-error'}>
            {status.key_set ? 'set' : 'not set'}
          </span>
          {' · '}source: <span className="font-mono">{status.source}</span>
        </p>
      )}
      <div className="space-y-3 mb-4">
        <label className="block" htmlFor="cfg-model-select">
          <span className="text-text-secondary text-xs">Model</span>
          <select id="cfg-model-select" data-testid="cfg-model-select" value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className="mt-1 w-full border border-border rounded px-2 py-1.5 text-sm bg-surface text-text">
            {Object.entries(models.reduce((acc, m) => {
              (acc[m.group] ||= []).push(m); return acc;
            }, {})).map(([group, items]) => (
              <optgroup key={group} label={group}>
                {items.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
              </optgroup>
            ))}
          </select>
        </label>
        {(() => {
          const sel = models.find((m) => m.id === modelId);
          return sel?.base_url ? (
            <p className="text-text-tertiary text-xs -mt-2">Endpoint: <span className="font-mono">{sel.base_url}</span></p>
          ) : null;
        })()}
        <label className="block" htmlFor="cfg-apikey">
          <span className="text-text-secondary text-xs">API key</span>
          <input id="cfg-apikey" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
            placeholder="leave blank to keep current" autoComplete="new-password"
            className="mt-1 w-full border border-border rounded px-2 py-1.5 text-sm bg-surface text-text" />
        </label>
        <label className="flex items-center gap-2 pt-1" htmlFor="cfg-reasoning">
          <input id="cfg-reasoning" type="checkbox" checked={showReasoning}
            onChange={(e) => setShowReasoning(e.target.checked)}
            className="h-4 w-4 accent-primary" data-testid="cfg-reasoning" />
          <span className="text-text-secondary text-xs">
            Show model reasoning
            <span className="block text-text-tertiary">Anthropic only — streams the model's thinking (uses extra tokens)</span>
          </span>
        </label>
      </div>
      {notice && (
        <p className={`mb-3 text-xs ${notice.type === 'ok' ? 'text-success' : 'text-error'}`}>{notice.text}</p>
      )}
      <div className="flex gap-2">
        <Button variant="primary" onClick={handleSave} className="flex-1">Save</Button>
        <Button variant="secondary" onClick={handleReset} className="flex-1">Reset to env defaults</Button>
      </div>
    </div>
  );
}
