import Skeleton from './ui/Skeleton';

// Loading placeholder for the flow canvas — a faux top-down node chain so the
// app doesn't flash blank while a bot is built/loaded/analyzed.
export default function FlowSkeleton() {
  return (
    <div data-testid="flow-skeleton" className="h-full w-full overflow-hidden p-8">
      <div className="flex flex-col items-center gap-5">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex w-full max-w-sm flex-col items-center gap-5">
            <Skeleton className="h-16 w-64" />
            {i < 3 && <Skeleton className="h-6 w-0.5" />}
          </div>
        ))}
      </div>
      <p className="mt-8 text-center text-sm text-text-tertiary">Analyzing…</p>
    </div>
  );
}
