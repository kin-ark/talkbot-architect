/* eslint-disable react-refresh/only-export-components -- provider file; useConfirm hook is intentionally co-located with ConfirmProvider */
import { createContext, useCallback, useContext, useRef, useState } from 'react';
import ConfirmDialog from '../components/ConfirmDialog';

const ConfirmContext = createContext(null);

export function ConfirmProvider({ children }) {
  const [request, setRequest] = useState(null);
  const resolverRef = useRef(null);

  const settle = useCallback((value) => {
    const resolve = resolverRef.current;
    resolverRef.current = null;
    setRequest(null);
    if (resolve) resolve(value);          // guarded: only the first call has a resolver
  }, []);

  const confirm = useCallback((opts) => new Promise((resolve) => {
    // Supersede any open request (resolve it false) before opening the new one.
    if (resolverRef.current) { const prev = resolverRef.current; resolverRef.current = null; prev(false); }
    resolverRef.current = resolve;
    setRequest(opts);
  }), []);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {request && (
        <ConfirmDialog {...request}
          onConfirm={() => settle(true)}
          onCancel={() => settle(false)} />
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  // Graceful fallback when not wrapped in a provider (keeps unwrapped renders working).
  return ctx || ((opts) => Promise.resolve(window.confirm(opts?.message || 'Are you sure?')));
}
