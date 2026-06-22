import { useState } from 'react';
export default function SettingsPopover() {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} className="px-2 py-1 text-sm rounded hover:bg-slate-100">⚙</button>
      {open && (
        <div className="absolute right-0 mt-2 w-64 bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-xs text-slate-600 z-10">
          <p className="font-semibold mb-1">LLM provider</p>
          <p>Configured server-side via <code>LLM_PROVIDER</code> + API key env vars (anthropic / openai).</p>
          <p className="mt-2 text-slate-400">Set <code>ANTHROPIC_API_KEY</code> or <code>OPENAI_API_KEY</code> before starting the backend.</p>
        </div>
      )}
    </div>
  );
}
