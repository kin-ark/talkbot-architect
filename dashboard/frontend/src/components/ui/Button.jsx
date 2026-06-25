const VARIANTS = {
  primary: 'bg-primary text-primary-fg hover:bg-primary-hover',
  secondary: 'bg-surface border border-border text-text-secondary hover:bg-surface-muted',
  ghost: 'text-text-secondary hover:bg-surface-muted',
};
export default function Button({ variant = 'primary', className = '', children, ...props }) {
  return (
    <button {...props}
      className={`rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-40 ${VARIANTS[variant] || VARIANTS.primary} ${className}`}>
      {children}
    </button>
  );
}
