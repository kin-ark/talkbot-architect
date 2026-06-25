import { useState, useEffect } from 'react';
import { getConfig, updateConfig, clearConfig } from '../api';

const PROVIDERS = ['anthropic', 'openai', 'openai-compatible'];

export default function SettingsPopover() {
  const [open, setOpen] = useState(false);

  // Current config state (from backend)
  const [status, setStatus] = useState(null); // {provider, model, base_url, key_set, source}
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null); // {type: 'ok'|'err', text}

  // Form field state — api_key is NEVER seeded from backend
  const [provider, setProvider] = useState('anthropic');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState(''); // always starts blank

  // Fetch config whenever the popover opens
  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- legitimate async-fetch loader pattern; setLoading/setNotice reset before an async call, not as a derived-state sync
    setLoading(true);
    setNotice(null);
    getConfig()
      .then((cfg) => {
        setStatus(cfg);
        setProvider(cfg.provider || 'anthropic');
        setModel(cfg.model || '');
        setBaseUrl(cfg.base_url || '');
        // api_key intentionally NOT set — backend never returns it
      })
      .catch(() => setNotice({ type: 'err', text: 'Failed to load config.' }))
      .finally(() => setLoading(false));
  }, [open]);

  const handleSave = async () => {
    setNotice(null);
    const payload = { provider, model };
    if (baseUrl) payload.base_url = baseUrl;
    if (apiKey) payload.api_key = apiKey; // omit when blank → keep current
    try {
      const cfg = await updateConfig(payload);
      setStatus(cfg);
      setApiKey(''); // clear after save
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
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="⚙"
        className="px-2 py-1 text-sm rounded hover:bg-surface-muted text-text-secondary"
      >
        ⚙
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-surface border border-border rounded-lg shadow-card p-4 text-xs text-text z-10">
          <p className="font-semibold text-sm mb-3 text-text">AI settings</p>

          {loading && <p className="text-text-tertiary mb-2">Loading…</p>}

          {status && (
            <p className="mb-3 text-text-secondary">
              API key:{' '}
              <span className={status.key_set ? 'text-success font-medium' : 'text-error'}>
                {status.key_set ? 'set ✓' : 'not set'}
              </span>
              {' · '}source: <span className="font-mono">{status.source}</span>
            </p>
          )}

          <div className="space-y-2 mb-3">
            <label className="block">
              <span className="text-text-secondary">Provider</span>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="mt-1 w-full border border-border rounded px-2 py-1 text-xs bg-surface text-text"
              >
                {PROVIDERS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-text-secondary">Model</span>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="e.g. claude-opus-4-8, gpt-4o"
                className="mt-1 w-full border border-border rounded px-2 py-1 text-xs bg-surface text-text"
              />
            </label>

            <label className="block">
              <span className="text-text-secondary">Base URL</span>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="optional — for gateways / OpenAI-compatible endpoints"
                className="mt-1 w-full border border-border rounded px-2 py-1 text-xs bg-surface text-text"
              />
            </label>

            <label className="block">
              <span className="text-text-secondary">API key</span>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="leave blank to keep current"
                autoComplete="new-password"
                className="mt-1 w-full border border-border rounded px-2 py-1 text-xs bg-surface text-text"
              />
            </label>
          </div>

          {notice && (
            <p className={`mb-2 ${notice.type === 'ok' ? 'text-success' : 'text-error'}`}>
              {notice.text}
            </p>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="flex-1 bg-primary text-primary-fg rounded px-3 py-1 text-xs hover:bg-primary-hover"
            >
              Save
            </button>
            <button
              onClick={handleReset}
              className="flex-1 border border-border rounded px-3 py-1 text-xs text-text-secondary hover:bg-surface-muted"
            >
              Reset to env defaults
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
