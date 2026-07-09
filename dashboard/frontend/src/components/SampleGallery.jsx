import { useState, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import { listSamples } from '../api';

const GROUPS = [
  ['Debt Collection', (s) => s.id.startsWith('debt_')],
  ['Starters', () => true],
];

export default function SampleGallery({ onPick }) {
  const [samples, setSamples] = useState([]);
  useEffect(() => {
    let off = false;
    listSamples().then((s) => { if (!off) setSamples(Array.isArray(s) ? s : []); }).catch(() => {});
    return () => { off = true; };
  }, []);
  if (!samples.length) return null;

  const used = new Set();
  const grouped = GROUPS.map(([label, pred]) => {
    const items = samples.filter((s) => !used.has(s.id) && pred(s));
    items.forEach((s) => used.add(s.id));
    return [label, items];
  }).filter(([, items]) => items.length);

  return (
    <div data-testid="sample-gallery" className="mt-4 space-y-4">
      {grouped.map(([label, items]) => (
        <div key={label}>
          <div className="text-xs font-semibold uppercase tracking-wide text-text-tertiary mb-2">{label}</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {items.map((s) => (
              <button type="button" key={s.id} data-testid="sample-card" onClick={() => onPick(s.id)}
                className="flex items-start gap-2 text-left rounded-lg border border-border bg-surface hover:bg-surface-muted px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                <Sparkles size={16} className="mt-0.5 shrink-0 text-primary" />
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-text line-clamp-2">{s.title}</span>
                  <span className="block text-xs text-text-secondary line-clamp-2">{s.description}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
