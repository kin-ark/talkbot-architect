// Turn a raw error string (usually str(exception) from the backend LLM client,
// or an axios errText) into a friendly {title, hint} plus the original detail.
// Pure + exhaustively defaulted so the renderer never shows a bare stack trace.

const RULES = [
  {
    title: 'Authentication failed',
    hint: 'Check the API key for this provider in Settings.',
    test: (t) => /\b401\b|\b403\b|authentication_error|permission_error|invalid[_ ]?x-?api-?key|invalid api key|unauthorized|no ai key/.test(t),
  },
  {
    title: 'Rate limited',
    hint: 'Too many requests — wait a few seconds and retry.',
    test: (t) => /\b429\b|rate[_ ]?limit/.test(t),
  },
  {
    title: 'Model overloaded',
    hint: 'The provider is busy right now — retry in a moment.',
    test: (t) => /\b529\b|overloaded|no available accounts/.test(t),
  },
  {
    title: 'Provider server error',
    hint: 'The model provider had a server error — retry shortly.',
    test: (t) => /\b5(00|02|03|04)\b|internal server error|bad gateway|service unavailable|gateway timeout/.test(t),
  },
  {
    title: 'Connection problem',
    hint: "Couldn't reach the model — check your network and the Base URL in Settings.",
    test: (t) => /connection error|econnrefused|enotfound|network|timed out|timeout|fetch failed/.test(t),
  },
  {
    title: 'Conversation too long',
    hint: "This turn exceeded the model's context limit — start a new session or shorten the input.",
    test: (t) => /context length|maximum context|prompt is too long|too many tokens|context_length_exceeded/.test(t),
  },
  {
    title: "Model can't read images",
    hint: 'Pick a Claude vision model in Settings, or remove the image.',
    test: (t) => /can'?t read images|does not support image|vision/.test(t),
  },
  {
    title: 'No bot loaded',
    hint: 'Upload an export or start a new bot first.',
    test: (t) => /no session loaded|no bot loaded/.test(t),
  },
  {
    title: 'Request cancelled',
    hint: null,
    test: (t) => /\bcanceled\b|\bcancelled\b|aborted/.test(t),
  },
];

export function classifyError(raw) {
  const detail = (raw == null ? '' : String(raw)).trim();
  const t = detail.toLowerCase();
  for (const r of RULES) {
    if (r.test(t)) return { title: r.title, hint: r.hint, detail };
  }
  return { title: 'Something went wrong', hint: null, detail: detail || 'Request failed.' };
}
