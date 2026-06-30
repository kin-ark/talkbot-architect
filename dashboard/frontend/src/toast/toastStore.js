// Dependency-free observable toast store. `toast.*` is callable from anywhere
// (components, hooks, plain modules). Rendered by <ToastViewport>.
let _id = 0;
let _toasts = [];                  // current snapshot (replaced, never mutated)
const _listeners = new Set();
const _timers = new Map();         // id -> timeout handle

const DEFAULT_MS = 4000;
const ERROR_MS = 6000;

function _emit() {
  for (const fn of _listeners) fn();
}

export function subscribe(fn) {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

export function getSnapshot() {
  return _toasts;                  // stable ref until a mutation replaces it
}

export function push(kind, message, { duration } = {}) {
  const id = ++_id;
  _toasts = [..._toasts, { id, kind, message }];
  _emit();
  const ms = duration === undefined ? DEFAULT_MS : duration;
  if (ms > 0) {
    _timers.set(id, setTimeout(() => dismiss(id), ms));
  }
  return id;
}

export function dismiss(id) {
  const t = _timers.get(id);
  if (t) { clearTimeout(t); _timers.delete(id); }
  const next = _toasts.filter((x) => x.id !== id);
  if (next.length !== _toasts.length) { _toasts = next; _emit(); }
}

export const toast = {
  success: (m, o) => push('success', m, o),
  error: (m, o) => push('error', m, { duration: ERROR_MS, ...o }),
  info: (m, o) => push('info', m, o),
  dismiss,
};
