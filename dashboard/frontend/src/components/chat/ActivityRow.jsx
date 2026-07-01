import { useState } from 'react';
import { Loader2, Check, AlertCircle, ChevronRight, ChevronDown } from 'lucide-react';
import { narrate } from './narration';

function safeStringify(v) {
  try { return JSON.stringify(v, null, 2); } catch { return String(v); }
}
function fmt(v) {
  return typeof v === 'string' ? v : safeStringify(v);
}
function errorish(result) {
  if (typeof result === 'string') return /error|failed|exception/i.test(result);
  if (result && typeof result === 'object') return Boolean(result.error) || result.ok === false;
  return false;
}
function hasArgs(args) {
  return args && typeof args === 'object' && Object.keys(args).length > 0;
}

export default function ActivityRow({ entry }) {
  const [open, setOpen] = useState(false);
  const { name, arguments: args, status, summary, result } = entry || {};
  const running = status === 'running';
  const isErr = !running && errorish(result);

  const Glyph = running ? Loader2 : isErr ? AlertCircle : Check;
  const glyphClass = running ? 'text-text-secondary animate-spin' : isErr ? 'text-error' : 'text-success';
  const Caret = open ? ChevronDown : ChevronRight;

  return (
    <div className="text-xs">
      <button type="button" data-testid="activity-row" onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-1.5 py-0.5 text-left text-text-secondary hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded">
        <Caret size={12} className="shrink-0 text-text-tertiary" />
        <Glyph size={13} className={`shrink-0 ${glyphClass}`} />
        <span className="text-text">{narrate(name)}</span>
        {!running && summary && <span className="text-text-tertiary truncate">— {summary}</span>}
      </button>
      {open && (
        <div data-testid="activity-detail" className="ml-5 mt-0.5 space-y-1">
          {hasArgs(args) && (
            <div>
              <div className="text-text-tertiary">Input</div>
              <pre className="max-h-48 overflow-auto text-[11px] leading-relaxed rounded bg-surface-muted text-text p-2 m-0 whitespace-pre-wrap break-words">{fmt(args)}</pre>
            </div>
          )}
          {result != null && (
            <div>
              <div className="text-text-tertiary">Output</div>
              <pre className="max-h-48 overflow-auto text-[11px] leading-relaxed rounded bg-surface-muted text-text p-2 m-0 whitespace-pre-wrap break-words">{fmt(result)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
