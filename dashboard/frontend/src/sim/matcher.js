// Mode B: match a typed caller utterance to a talk branch via its intents'
// keyword / user_response training. Pure — no React / fetch / DOM.
import { intentsForBranch } from './prep';

const FALLBACK_LABELS = new Set(['Unclassified', 'Default']);

function tokens(s) {
  return String(s ?? '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
}

export function matchUtterance(utterance, node, intentsById) {
  const uNorm = String(utterance ?? '').toLowerCase().trim();
  if (!uNorm) return null;
  const uTokens = new Set(tokens(uNorm));
  const branches = node?.branches || [];
  let best = null; // { branchIndex, intentName, score }
  branches.forEach((b, i) => {
    if (FALLBACK_LABELS.has(b.label)) return;
    let score = 0;
    let hitName = null;
    for (const id of intentsForBranch(node, b.label)) {
      const intent = intentsById.get(String(id));
      if (!intent) continue;
      for (const kw of intent.keywords || []) {
        const k = String(kw).toLowerCase().trim();
        if (!k) continue;
        const kTokens = tokens(k);
        const hit = uNorm.includes(k) || (kTokens.length > 0 && kTokens.every((t) => uTokens.has(t)));
        if (hit) { score += 2; if (!hitName) hitName = intent.name; }
      }
      for (const ur of intent.user_responses || []) {
        const rTokens = tokens(ur).filter((t) => t.length >= 3);
        if (rTokens.some((t) => uTokens.has(t))) { score += 1; if (!hitName) hitName = intent.name; }
      }
    }
    if (score > 0 && (!best || score > best.score)) {
      best = { branchIndex: i, intentName: hitName, score };
    }
  });
  return best;
}
