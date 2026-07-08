// Pulsing placeholder block for loading states. Lark tokens, light+dark.
export default function Skeleton({ className = '' }) {
  return (
    <div aria-hidden="true" className={`animate-pulse rounded-md bg-surface-muted ${className}`} />
  );
}
