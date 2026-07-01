import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import ActivityRow from './ActivityRow';
import { narrate } from './narration';

export default function ToolTrace({ trace }) {
  const runningEntry = (trace || []).find((t) => t.status === 'running');
  const running = Boolean(runningEntry);
  const [open, setOpen] = useState(running);
  if (!trace || trace.length === 0) return null;
  const expanded = open || running;
  const n = trace.length;
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
        {expanded ? '▾' : '▸'} {n} tool{n === 1 ? '' : 's'}
      </button>
      {expanded && (
        <div data-testid="tool-trace" className="mt-1 space-y-0.5">
          {trace.map((t, j) => <ActivityRow key={j} entry={t} />)}
        </div>
      )}
    </div>
  );
}
