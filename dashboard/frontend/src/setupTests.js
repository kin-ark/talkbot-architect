import '@testing-library/jest-dom';

// Polyfill ResizeObserver for @xyflow/react in jsdom
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
