import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import SettingsPage from './SettingsPage';

beforeEach(() => {
  vi.clearAllMocks();
  api.getConfig.mockResolvedValue({ provider: 'anthropic', model: 'claude-x', base_url: null, key_set: true, source: 'env' });
  api.updateConfig.mockResolvedValue({ provider: 'openai', model: 'gpt-y', base_url: null, key_set: true, source: 'override' });
  api.clearConfig.mockResolvedValue({ provider: 'anthropic', model: 'claude-x', base_url: null, key_set: true, source: 'env' });
});

describe('SettingsPage', () => {
  it('loads current config on mount', async () => {
    render(<SettingsPage />);
    await waitFor(() => expect(api.getConfig).toHaveBeenCalled());
    expect(screen.getByDisplayValue('claude-x')).toBeInTheDocument();
  });
  it('Save sends provider/model to updateConfig', async () => {
    render(<SettingsPage />);
    await waitFor(() => expect(api.getConfig).toHaveBeenCalled());
    fireEvent.change(screen.getByLabelText(/model/i), { target: { value: 'gpt-y' } });
    fireEvent.click(screen.getByText('Save'));
    await waitFor(() => expect(api.updateConfig).toHaveBeenCalledWith(expect.objectContaining({ model: 'gpt-y' })));
  });
  it('Reset calls clearConfig', async () => {
    render(<SettingsPage />);
    await waitFor(() => expect(api.getConfig).toHaveBeenCalled());
    fireEvent.click(screen.getByText(/Reset to env defaults/i));
    await waitFor(() => expect(api.clearConfig).toHaveBeenCalled());
  });
});
