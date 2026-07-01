import { useState } from 'react';
import ToolChip from '../ToolChip';

export default function ToolTrace({ trace }) {
  const running = (trace || []).some((t) => t.status === 'running');
  const [open, setOpen] = useState(running);
  if (!trace || trace.length === 0) return null;
  const expanded = open || running;
  const n = trace.length;
  return (
    <div className="mb-1">
      <button type="button" data-testid="tool-trace-toggle" onClick={() => setOpen((v) => !v)}
        className="text-xs text-text-secondary hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
        {expanded ? '▾' : '▸'} {n} tool{n === 1 ? '' : 's'}
      </button>
      {expanded && (
        <div data-testid="tool-trace" className="mt-1">
          {trace.map((t, j) => <ToolChip key={j} name={t.name} args={t.arguments} status={t.status} summary={t.summary} />)}
        </div>
      )}
    </div>
  );
}
