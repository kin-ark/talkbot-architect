export default function Tabs({ tabs, active, onChange }) {
  const onKeyDown = (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const i = tabs.findIndex((t) => t.id === active);
    if (i < 0) return;
    const next = e.key === 'ArrowRight'
      ? tabs[(i + 1) % tabs.length]
      : tabs[(i - 1 + tabs.length) % tabs.length];
    onChange(next.id);
  };

  return (
    <div role="tablist" onKeyDown={onKeyDown} className="flex gap-1 p-1.5 border-b border-divider">
      {tabs.map((t) => {
        const selected = active === t.id;
        return (
          <button key={t.id} role="tab" aria-selected={selected} tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.id)}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${
              selected ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted'}`}>
            {t.label}
            {t.badge != null && (
              <span className="rounded-full bg-error text-primary-fg text-[10px] px-1.5 leading-4">{t.badge}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
