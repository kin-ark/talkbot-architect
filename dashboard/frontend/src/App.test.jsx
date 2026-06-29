import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
vi.mock('./api');
import * as api from './api';
import App from './App';

beforeEach(() => {
  api.getConfig.mockResolvedValue({ key_set: true });
  api.listSamples.mockResolvedValue([]);
});

describe('App', () => {
  it('shows the upload zone before any session', () => {
    render(<App />);
    expect(screen.getByTestId('upload-zone')).toBeInTheDocument();
  });
});
