export default function ComponentsRail({ summary, selectedComponentId, onSelectComponent, onAddComponent }) {
  const components = summary?.components || [];
  return (
    <div className="w-56 shrink-0 h-full border-r border-border bg-surface flex flex-col" data-testid="components-rail">
      <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-text-tertiary border-b border-divider">
        Components
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {components.map((c) => {
          const count = Object.keys(c.nodes || {}).length;
          const active = c.uuid === selectedComponentId;
          return (
            <button key={c.uuid} onClick={() => onSelectComponent(c.uuid)}
              className={`w-full flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-left ${
                active ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted'}`}>
              <span className="truncate">{c.name}</span>
              <span className="ml-auto text-xs text-text-tertiary">{count}</span>
            </button>
          );
        })}
        {components.length === 0 && (
          <p className="px-2 py-3 text-xs text-text-tertiary">No components yet.</p>
        )}
      </div>
      <div className="p-2 border-t border-divider">
        <button onClick={onAddComponent}
          className="w-full rounded-md px-2.5 py-1.5 text-sm text-primary hover:bg-surface-muted text-left">
          + Add component
        </button>
      </div>
    </div>
  );
}
