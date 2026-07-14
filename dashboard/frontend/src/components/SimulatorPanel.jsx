import { useState, useMemo } from 'react';
import { Play, RotateCcw, X } from 'lucide-react';
import { neededVars, defaultStartComponent } from '../sim/prep';
import { start as simStart, choose as simChoose } from '../sim/engine';

const END_LABEL = {
  hangup: 'Call ended — hang up',
  transfer: 'Transferred to a human agent',
  external: 'Left this export (library/external)',
  loop_guard: 'Loop guard hit — possible cycle',
  dead_end: 'Dead end — a branch had no target',
  no_entry: 'No entry node',
  talk_continue: 'Waiting for the caller (talk-continue)',
  ended: 'Call ended',
};

export default function SimulatorPanel({ summary, onCurrentNode }) {
  const components = summary?.components || [];
  const [startComp, setStartComp] = useState(() => defaultStartComponent(summary) || '');
  const vars = useMemo(() => neededVars(summary), [summary]);
  const [varInputs, setVarInputs] = useState({});
  const [state, setState] = useState(null);
  const [showVars, setShowVars] = useState(false);

  const push = (next) => { setState(next); onCurrentNode?.(next.status === 'ended' ? null : next.nodeUuid); };
  const begin = () => push(simStart(summary, startComp, varInputs));
  const pick = (i) => push(simChoose(state, summary, i));
  const exitSim = () => { setState(null); onCurrentNode?.(null); };

  if (!summary || components.length === 0) {
    return <div className="p-4 text-sm text-text-tertiary" data-testid="sim-empty">Load or build a bot first.</div>;
  }

  if (!state) {
    return (
      <div className="p-4 space-y-3 overflow-y-auto h-full" data-testid="sim-setup">
        <label className="block text-xs text-text-secondary">Start component
          <select value={startComp} onChange={(e) => setStartComp(e.target.value)}
            className="mt-1 w-full border border-border rounded-md px-2 py-1 text-sm bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary">
            {components.map((c) => <option key={c.uuid} value={c.uuid}>{c.name}</option>)}
          </select>
        </label>
        {vars.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-text-tertiary">These aren&rsquo;t set by the flow — fill them to steer conditionals.</div>
            {vars.map((v) => (
              <label key={v} className="block text-xs text-text-secondary">{v}
                <input value={varInputs[v] || ''} onChange={(e) => setVarInputs((s) => ({ ...s, [v]: e.target.value }))}
                  className="mt-1 w-full border border-border rounded-md px-2 py-1 text-sm bg-surface text-text focus:outline-none focus:ring-2 focus:ring-primary" />
              </label>
            ))}
          </div>
        )}
        <button type="button" onClick={begin} data-testid="sim-start"
          className="inline-flex items-center gap-1.5 px-3 h-[34px] bg-primary text-primary-fg rounded-lg hover:bg-primary-hover text-sm">
          <Play size={14} /> Start
        </button>
      </div>
    );
  }

  const showHeader = state.status !== 'ended';

  return (
    <div className="flex flex-col h-full" data-testid="sim-running">
      {showHeader && (
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
          <span className="text-xs text-text-secondary">Simulating</span>
          <button type="button" onClick={begin}
            className="ml-auto inline-flex items-center gap-1 text-xs text-primary hover:underline">
            <RotateCcw size={12} /> Restart
          </button>
          <button type="button" onClick={exitSim}
            className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-text">
            <X size={12} /> Exit
          </button>
        </div>
      )}

      {Object.keys(state.varState || {}).length > 0 && (
        <details className="px-3 py-1 border-b border-border text-xs text-text-tertiary" onToggle={(e) => setShowVars(e.currentTarget.open)}>
          <summary className="cursor-pointer select-none">Variables ({Object.keys(state.varState).length})</summary>
          {showVars && (
            <div className="mt-1 space-y-0.5">
              {Object.entries(state.varState).map(([k, v]) => (
                <div key={k}><span className="font-mono">{k}</span> = {String(v)}</div>
              ))}
            </div>
          )}
        </details>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2" data-testid="sim-transcript">
        {state.transcript.map((row, i) => {
          if (row.role === 'bot') {
            return (
              <div key={i} className="text-left">
                <div className="text-[11px] text-text-tertiary">{row.label}</div>
                <div className="inline-block max-w-[85%] p-2 rounded-lg text-sm bg-surface border border-border text-text whitespace-pre-wrap">{row.text || '(no text)'}</div>
              </div>
            );
          }
          if (row.role === 'you') {
            return (
              <div key={i} className="text-right">
                <span className="inline-block px-2 py-1 rounded-lg text-sm bg-primary text-primary-fg">{row.label}</span>
              </div>
            );
          }
          return <div key={i} className="text-xs italic text-text-tertiary px-1">{row.text}</div>;
        })}
      </div>

      {state.status === 'awaiting_choice' && (
        <div className="p-3 border-t border-border flex flex-wrap gap-2" data-testid="sim-choices">
          {state.choices.map((c) => (
            <button key={c.branchIndex} type="button" disabled={c.disabled} onClick={() => pick(c.branchIndex)}
              title={c.reason || ''} data-testid="sim-choice"
              className={`text-xs rounded-full border px-3 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                c.disabled ? 'border-border text-text-tertiary opacity-50 cursor-not-allowed'
                : c.label === 'Unclassified' ? 'border-border text-text-tertiary hover:bg-surface-muted'
                : 'border-primary text-primary hover:bg-primary/10'}`}>
              {c.label}{c.disabled ? ' (dead end)' : ''}
            </button>
          ))}
        </div>
      )}

      {state.status === 'ended' && (
        <div className="p-3 border-t border-border" data-testid="sim-ended">
          <div className="text-sm text-text-secondary">{END_LABEL[state.endReason] || 'Call ended'}</div>
          <button type="button" onClick={begin}
            className="mt-2 inline-flex items-center gap-1.5 px-3 h-[32px] bg-primary text-primary-fg rounded-lg hover:bg-primary-hover text-sm">
            <RotateCcw size={14} /> Restart
          </button>
        </div>
      )}
    </div>
  );
}
