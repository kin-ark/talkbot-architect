import { useRef, useState, useEffect, useCallback } from 'react';

const THRESHOLD = 80;

export function useChatScroll(dep) {
  const scrollRef = useRef(null);
  const nearBottomRef = useRef(true);
  const [atBottom, setAtBottom] = useState(true);

  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < THRESHOLD;
    nearBottomRef.current = near;
    setAtBottom(near);
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (el.scrollTo) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    else el.scrollTop = el.scrollHeight;
    el.scrollTop = el.scrollHeight;          // jsdom-safe immediate set
    nearBottomRef.current = true;
    setAtBottom(true);
  }, []);

  // Autoscroll on new content only when already near the bottom.
  useEffect(() => {
    const el = scrollRef.current;
    if (el && nearBottomRef.current) el.scrollTop = el.scrollHeight;
  }, [dep]);

  return { scrollRef, onScroll, atBottom, scrollToBottom };
}
