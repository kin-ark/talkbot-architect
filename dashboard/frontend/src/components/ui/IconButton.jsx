export default function IconButton({ label, className = '', children, ...props }) {
  return (
    <button aria-label={label} title={label} {...props}
      className={`h-8 w-8 inline-flex items-center justify-center rounded-md text-text-secondary hover:bg-surface-muted ${className}`}>
      {children}
    </button>
  );
}
