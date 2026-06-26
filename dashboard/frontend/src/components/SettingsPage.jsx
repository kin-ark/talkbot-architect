import { useState, useEffect } from 'react';
import { getConfig, updateConfig, clearConfig } from '../api';
import Button from './ui/Button';

const PROVIDERS = ['anthropic', 'openai', 'openai-compatible'];

export default function SettingsPage() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null);
  const [provider, setProvider] = useState('anthropic');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- legitimate async-fetch loader pattern; setLoading/setNotice reset before an async call, not as a derived-state sync
    setLoading(true);
    setNotice(null);
    getConfig()
      .then((cfg) => {
        if (cancelled) return;
        setStatus(cfg);
        setProvider(cfg.provider || 'anthropic');
        setModel(cfg.model || '');
        setBaseUrl(cfg.base_url || '');
      })
      .catch(() => { if (!cancelled) setNotice({ type: 'err', text: 'Failed to load config.' }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const handleSave = async () => {
    setNotice(null);
    const payload = { provider, model };
    if (baseUrl) payload.base_url = baseUrl;
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
      setProvider(cfg.provider || 'anthropic');
      setModel(cfg.model || '');
      setBaseUrl(cfg.base_url || '');
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
        <label className="block" htmlFor="cfg-provider">
          <span className="text-text-secondary text-xs">Provider</span>
          <select id="cfg-provider" value={provider} onChange={(e) => setProvider(e.target.value)}
            className="mt-1 w-full border border-border rounded px-2 py-1.5 text-sm bg-surface text-text">
            {PROVIDERS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </label>
        <label className="block" htmlFor="cfg-model">
          <span className="text-text-secondary text-xs">Model</span>
          <input id="cfg-model" type="text" value={model} onChange={(e) => setModel(e.target.value)}
            placeholder="e.g. claude-opus-4-8, gpt-4o"
            className="mt-1 w-full border border-border rounded px-2 py-1.5 text-sm bg-surface text-text" />
        </label>
        <label className="block" htmlFor="cfg-baseurl">
          <span className="text-text-secondary text-xs">Base URL</span>
          <input id="cfg-baseurl" type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="optional — for gateways / OpenAI-compatible endpoints"
            className="mt-1 w-full border border-border rounded px-2 py-1.5 text-sm bg-surface text-text" />
        </label>
        <label className="block" htmlFor="cfg-apikey">
          <span className="text-text-secondary text-xs">API key</span>
          <input id="cfg-apikey" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
            placeholder="leave blank to keep current" autoComplete="new-password"
            className="mt-1 w-full border border-border rounded px-2 py-1.5 text-sm bg-surface text-text" />
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
