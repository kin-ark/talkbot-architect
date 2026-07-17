// Pure mapping from a turn's failure signal to an ordered list of recovery
// action tokens. Backend may suggest an explicit `recovery` list; otherwise we
// derive from stop_reason / error.kind. Unknown tokens are dropped so the UI is
// forward-compatible with future backend tokens it doesn't render yet.

export const KNOWN_TOKENS = ['retry', 'continue', 'fix', 'edit', 'discard'];

export const CANNED = {
  continue: 'continue',
  fix: 'Fix the errors in the current proposal and re-propose.',
};

export function tokensFor({ kind, recovery, stopReason } = {}) {
  if (Array.isArray(recovery) && recovery.length) {
    return recovery.filter((t) => KNOWN_TOKENS.includes(t));
  }
  if (stopReason === 'limit') return ['continue'];
  switch (kind) {
    case 'transient': return ['retry'];
    case 'proposal_blocked': return ['fix', 'discard'];
    case 'tool_arg': return ['edit', 'retry'];
    default: return ['retry'];
  }
}
