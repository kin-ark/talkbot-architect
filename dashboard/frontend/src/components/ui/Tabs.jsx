export default function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 p-1.5 border-b border-divider">
      {tabs.map((t) => (
        <button key={t.id} onClick={() => onChange(t.id)}
          className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${
            active === t.id ? 'bg-surface-muted text-primary font-semibold' : 'text-text-secondary hover:bg-surface-muted'}`}>
          {t.label}
          {t.badge != null && (
            <span className="rounded-full bg-error text-primary-fg text-[10px] px-1.5 leading-4">{t.badge}</span>
          )}
        </button>
      ))}
    </div>
  );
}
