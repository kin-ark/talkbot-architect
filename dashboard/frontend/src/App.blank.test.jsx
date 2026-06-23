import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import * as api from './api';

vi.mock('./api', () => ({
  __esModule: true,
  startBlank: vi.fn().mockResolvedValue({ summary: { components: [] }, findings: [] }),
  getConfig: vi.fn().mockResolvedValue({}),
  exportUrl: vi.fn(() => '/export'),
}));
import App from './App';

describe('App blank session', () => {
  it('shows a Start from scratch button on the landing screen', () => {
    render(<App />);
    expect(screen.getByText(/Start from scratch/i)).toBeInTheDocument();
  });
  it('clicking the button calls api.startBlank', async () => {
    render(<App />);
    const btn = screen.getByText(/Start from scratch/i);
    fireEvent.click(btn);
    await waitFor(() => {
      expect(api.startBlank).toHaveBeenCalled();
    });
  });
});
