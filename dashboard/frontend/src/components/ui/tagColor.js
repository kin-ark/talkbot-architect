// Deterministic tag category → color class (light+dark Lark tokens).
const _PALETTE = [
  'bg-primary/15 text-primary',
  'bg-success/15 text-success',
  'bg-warning/15 text-warning',
  'bg-error/15 text-error',
  'bg-surface-muted text-text-secondary',
];

export function tagColor(category) {
  let h = 0;
  for (let i = 0; i < (category || '').length; i++) {
    h = (h * 31 + category.charCodeAt(i)) >>> 0;
  }
  return _PALETTE[h % _PALETTE.length];
}
