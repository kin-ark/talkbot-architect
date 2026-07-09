import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
vi.mock('../api');
import * as api from '../api';
import EmptyState from './EmptyState';

const base = { keySet: true, loading: false, onUpload: () => {}, onStartBlank: () => {}, onLoadSample: () => {}, onOpenSettings: () => {} };

beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); api.listSamples.mockResolvedValue([]); });

describe('EmptyState', () => {
  it('renders the hero title, subtitle, upload zone, and start-from-scratch', () => {
    render(<EmptyState {...base} />);
    expect(screen.getByRole('heading', { name: 'Talkbot Architect' })).toBeInTheDocument();
    expect(screen.getByText(/the assistant builds and validates it for you/i)).toBeInTheDocument();
    expect(screen.queryByTestId('welcome-card')).toBeNull();
    expect(screen.getByTestId('upload-zone')).toBeInTheDocument();
    expect(screen.getByText(/Start from scratch/i)).toBeInTheDocument();
  });

  it('hides the key nudge when keySet is true', () => {
    render(<EmptyState {...base} keySet />);
    expect(screen.queryByTestId('key-nudge')).toBeNull();
  });

  it('shows the key nudge when keySet is false and "Open Settings" fires onOpenSettings', () => {
    const onOpenSettings = vi.fn();
    render(<EmptyState {...base} keySet={false} onOpenSettings={onOpenSettings} />);
    expect(screen.getByTestId('key-nudge')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Open Settings'));
    expect(onOpenSettings).toHaveBeenCalled();
  });

  it('"Start from scratch" fires onStartBlank', () => {
    const onStartBlank = vi.fn();
    render(<EmptyState {...base} onStartBlank={onStartBlank} />);
    fireEvent.click(screen.getByText(/Start from scratch/i));
    expect(onStartBlank).toHaveBeenCalled();
  });
});
