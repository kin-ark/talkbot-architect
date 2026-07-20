import { useEffect } from 'react';

const FOCUSABLE = [
  'a[href]', 'button:not([disabled])', 'textarea:not([disabled])',
  'input:not([disabled])', 'select:not([disabled])', '[tabindex]:not([tabindex="-1"])',
].join(',');

/**
 * Trap keyboard focus inside a modal container while it's open, and restore
 * focus to the previously-focused element (the trigger) on unmount.
 *
 * @param {React.RefObject} ref  ref to the modal container element
 * @param {boolean} autoFocus    focus the first focusable on open (default true)
 */
export function useFocusTrap(ref, autoFocus = true) {
  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const prev = document.activeElement;

    const items = () =>
      Array.from(node.querySelectorAll(FOCUSABLE))
        .filter((el) => el.getAttribute('aria-hidden') !== 'true');

    if (autoFocus) {
      const first = items()[0];
      (first || node).focus?.();
    }

    const onKey = (e) => {
      if (e.key !== 'Tab') return;
      const f = items();
      if (f.length === 0) { e.preventDefault(); return; }
      const firstEl = f[0];
      const lastEl = f[f.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };
    node.addEventListener('keydown', onKey);
    return () => {
      node.removeEventListener('keydown', onKey);
      prev?.focus?.();   // restore focus to the trigger
    };
  }, [ref, autoFocus]);
}
