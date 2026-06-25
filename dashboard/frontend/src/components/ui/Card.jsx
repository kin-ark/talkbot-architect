export default function Card({ className = '', children, ...props }) {
  return (
    <div {...props} className={`bg-surface border border-border rounded-lg shadow-card ${className}`}>
      {children}
    </div>
  );
}
