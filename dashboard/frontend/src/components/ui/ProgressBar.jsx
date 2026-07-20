// Dumb progress bar. Number value -> determinate fill; null -> indeterminate
// animated stripe. Tailwind + theme tokens, no emoji.
export default function ProgressBar({ value = null }) {
  const determinate = typeof value === 'number';
  const pct = determinate ? Math.max(0, Math.min(100, value)) : 0;
  return (
    <div role="progressbar" aria-valuemin={0} aria-valuemax={100}
      {...(determinate ? { 'aria-valuenow': pct } : {})}
      className="h-2 w-full overflow-hidden rounded-full bg-surface-muted">
      {determinate ? (
        <div data-testid="progress-fill" className="h-full rounded-full bg-primary transition-[width] duration-150"
          style={{ width: `${pct}%` }} />
      ) : (
        <div data-testid="progress-indeterminate"
          className="h-full w-1/3 rounded-full bg-primary animate-pulse" />
      )}
    </div>
  );
}
