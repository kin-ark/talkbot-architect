// @vitest-environment node
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import config from '../../tailwind.config.js';

describe('design tokens', () => {
  it('tailwind maps semantic colors to css vars + class dark mode', () => {
    expect(config.darkMode).toBe('class');
    expect(config.theme.extend.colors.primary.DEFAULT).toBe('var(--c-primary)');
    expect(config.theme.extend.colors.surface).toBe('var(--c-surface)');
    expect(config.theme.extend.colors.text.secondary).toBe('var(--c-text-2)');
    expect(config.theme.extend.boxShadow.card).toBe('var(--shadow-card)');
  });

  it('tokens.css defines light + dark values for the brand + surfaces', () => {
    const css = readFileSync(fileURLToPath(new URL('./tokens.css', import.meta.url)), 'utf8');
    expect(css).toContain('--c-primary: #3370FF');   // light brand
    expect(css).toMatch(/\.dark\s*\{[\s\S]*--c-surface: #1A1D23/);  // dark surface override
  });
});
