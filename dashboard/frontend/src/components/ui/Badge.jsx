const TONES = {
  neutral: 'bg-surface-muted text-text-secondary',
  success: 'bg-success-bg text-success',
  error: 'bg-error-bg text-error',
  warning: 'bg-warning-bg text-warning',
  primary: 'bg-surface-muted text-primary',
};
export default function Badge({ tone = 'neutral', className = '', children }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${TONES[tone] || TONES.neutral} ${className}`}>
      {children}
    </span>
  );
}
