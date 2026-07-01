export default function FilterChips({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-1" data-testid="filter-chips">
      {options.map(([id, label]) => (
        <button key={id} type="button" data-testid={`chip-${id}`} onClick={() => onChange(id)}
          className={`text-xs rounded-md px-2 py-0.5 border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
            value === id ? 'bg-primary text-primary-fg' : 'text-text-secondary hover:bg-surface-muted'}`}>
          {label}
        </button>
      ))}
    </div>
  );
}
