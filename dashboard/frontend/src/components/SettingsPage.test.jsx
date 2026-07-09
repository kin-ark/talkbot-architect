import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import SettingsPage from './SettingsPage';

beforeEach(() => {
  vi.clearAllMocks();
  api.getModels.mockResolvedValue({
    models: [
      { id: 'claude-opus-4-8', label: 'Claude Opus 4.8', provider: 'anthropic', base_url: null, group: 'Claude' },
      { id: 'gpt-4o', label: 'GPT-4o', provider: 'openai', base_url: null, group: 'OpenAI' },
    ],
    default: 'claude-opus-4-8',
  });
  api.getConfig.mockResolvedValue({ model_id: 'claude-opus-4-8', key_set: true, source: 'env', show_reasoning: false });
  api.updateConfig.mockResolvedValue({ model_id: 'gpt-4o', model: 'gpt-4o', key_set: true, source: 'override', show_reasoning: true });
  api.clearConfig.mockResolvedValue({ model_id: 'claude-opus-4-8', key_set: true, source: 'env', show_reasoning: false });
});

describe('SettingsPage', () => {
  it('loads current config on mount', async () => {
    render(<SettingsPage />);
    await waitFor(() => expect(api.getModels).toHaveBeenCalled());
    const select = await screen.findByTestId('cfg-model-select');
    expect(select.value).toBe('claude-opus-4-8');
  });
  it('renders the model dropdown and saves model_id', async () => {
    render(<SettingsPage />);
    const select = await screen.findByTestId('cfg-model-select');
    fireEvent.change(select, { target: { value: 'gpt-4o' } });
    fireEvent.click(screen.getByText('Save'));
    await waitFor(() => expect(api.updateConfig).toHaveBeenCalledWith(
      expect.objectContaining({ model_id: 'gpt-4o' })));
    // no free-text model input remains
    expect(screen.queryByPlaceholderText(/claude-opus-4-8, gpt-4o/)).toBeNull();
  });
  it('Reset calls clearConfig', async () => {
    render(<SettingsPage />);
    await waitFor(() => expect(api.getConfig).toHaveBeenCalled());
    fireEvent.click(screen.getByText(/Reset to env defaults/i));
    await waitFor(() => expect(api.clearConfig).toHaveBeenCalled());
  });

  it('renders show-reasoning from config and saves it', async () => {
    render(<SettingsPage />);
    const box = await screen.findByTestId('cfg-reasoning');
    expect(box).toBeInTheDocument();
    fireEvent.click(box);
    fireEvent.click(screen.getByText('Save'));
    await waitFor(() => expect(api.updateConfig).toHaveBeenCalledWith(expect.objectContaining({ show_reasoning: expect.any(Boolean) })));
  });
});
