import defaultTheme from 'tailwindcss/defaultTheme';

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter Variable"', 'Inter', ...defaultTheme.fontFamily.sans],
      },
      colors: {
        canvas: 'var(--c-canvas)',
        surface: 'var(--c-surface)',
        'surface-muted': 'var(--c-surface-muted)',
        border: 'var(--c-border)',
        divider: 'var(--c-divider)',
        text: {
          DEFAULT: 'var(--c-text)',
          secondary: 'var(--c-text-2)',
          tertiary: 'var(--c-text-3)',
        },
        primary: {
          DEFAULT: 'var(--c-primary)',
          hover: 'var(--c-primary-hover)',
          fg: 'var(--c-on-primary)',
        },
        success: { DEFAULT: 'var(--c-success)', bg: 'var(--c-success-bg)' },
        error: { DEFAULT: 'var(--c-error)', bg: 'var(--c-error-bg)' },
        warning: { DEFAULT: 'var(--c-warning)', bg: 'var(--c-warning-bg)' },
      },
      boxShadow: {
        card: 'var(--shadow-card)',
      },
    },
  },
  plugins: [],
}
