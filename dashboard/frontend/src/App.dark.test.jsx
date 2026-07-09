import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/react';
beforeEach(() => { global.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} }; });
vi.mock('./api');
import * as api from './api';
import App from './App';

describe('App dark mode', () => {
  it('renders without crashing under the .dark class', () => {
    api.getConfig?.mockResolvedValue?.({ provider: 'anthropic', model: 'm', base_url: null, key_set: true, source: 'env' });
    api.getModels?.mockResolvedValue?.({ models: [], custom_id: '' });
    api.listSamples?.mockResolvedValue?.([]);
    document.documentElement.classList.add('dark');
    const { container } = render(<App />);
    expect(container.querySelector('[data-testid]')).toBeTruthy();
    document.documentElement.classList.remove('dark');
  });
});
