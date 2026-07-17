import { useState } from 'react';
import { Loader2, Wrench } from 'lucide-react';
import ActivityRow from './ActivityRow';
import { narrate, narratePhase } from './narration';

function PhaseRow({ entry }) {
  return (
    <div className="flex items-center gap-1.5 py-0.5 text-xs text-text-secondary" data-testid="phase-row">
      <Wrench size={12} className="shrink-0 text-text-tertiary" />
      <span>{narratePhase(entry.phase, entry)}</span>
    </div>
  );
}

export default function ActivityTimeline({ trace }) {
  const runningEntry = (trace || []).find((t) => t._kind === 'tool' && t.status === 'running');
  const running = Boolean(runningEntry);
  const [open, setOpen] = useState(true);
  if (!trace || trace.length === 0) return null;
  const expanded = open || running;
  const toolCount = trace.filter((t) => t._kind === 'tool').length;
  return (
    <div className="mb-1">
      {running && (
        <div data-testid="activity-running" className="flex items-center gap-1.5 text-xs text-text-secondary mb-0.5">
          <Loader2 size={13} className="shrink-0 animate-spin" />
          <span>{narrate(runningEntry.name)}…</span>
        </div>
      )}
      <button type="button" data-testid="tool-trace-toggle" onClick={() => setOpen((v) => !v)}
        className="text-xs text-text-secondary hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
        {expanded ? '▾' : '▸'} {toolCount} tool{toolCount === 1 ? '' : 's'}
      </button>
      {expanded && (
        <div data-testid="tool-trace" className="mt-1 space-y-0.5">
          {trace.map((t, j) => (t._kind === 'phase'
            ? <PhaseRow key={j} entry={t} />
            : <ActivityRow key={j} entry={t} />))}
        </div>
      )}
    </div>
  );
}
