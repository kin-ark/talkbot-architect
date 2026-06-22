import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import SettingsPopover from './SettingsPopover';

vi.mock('../api', () => ({
  getConfig: vi.fn(),
  updateConfig: vi.fn(),
  clearConfig: vi.fn(),
}));

import { getConfig, updateConfig, clearConfig } from '../api';

const mockConfig = {
  provider: 'anthropic',
  model: 'claude-opus-4-8',
  base_url: null,
  key_set: true,
  source: 'env',
};

beforeEach(() => {
  vi.clearAllMocks();
  getConfig.mockResolvedValue(mockConfig);
  updateConfig.mockResolvedValue({ ...mockConfig, source: 'override' });
  clearConfig.mockResolvedValue(mockConfig);
});

describe('SettingsPopover', () => {
  it('calls getConfig and renders provider + key_set status when opened', async () => {
    render(<SettingsPopover />);
    fireEvent.click(screen.getByRole('button', { name: /⚙/i }));

    await waitFor(() => expect(getConfig).toHaveBeenCalledTimes(1));

    // provider shown in the select
    expect(screen.getByDisplayValue('anthropic')).toBeInTheDocument();
    // key_set shown as "set ✓"
    expect(screen.getByText(/set ✓/)).toBeInTheDocument();
  });

  it('api_key field is type="password" and is never pre-filled from getConfig response', async () => {
    render(<SettingsPopover />);
    fireEvent.click(screen.getByRole('button', { name: /⚙/i }));

    await waitFor(() => expect(getConfig).toHaveBeenCalledTimes(1));

    const keyInput = screen.getByPlaceholderText(/leave blank/i);
    expect(keyInput).toHaveAttribute('type', 'password');
    // must be empty — backend never returns key value
    expect(keyInput.value).toBe('');
  });

  it('Save calls updateConfig with entered values; omits api_key when blank', async () => {
    updateConfig.mockResolvedValue({ ...mockConfig, provider: 'openai', source: 'override' });

    render(<SettingsPopover />);
    fireEvent.click(screen.getByRole('button', { name: /⚙/i }));
    await waitFor(() => expect(getConfig).toHaveBeenCalledTimes(1));

    // Change provider
    fireEvent.change(screen.getByDisplayValue('anthropic'), { target: { value: 'openai' } });
    // Leave api_key blank
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(updateConfig).toHaveBeenCalledTimes(1));

    const payload = updateConfig.mock.calls[0][0];
    expect(payload.provider).toBe('openai');
    expect(payload).not.toHaveProperty('api_key'); // blank → omitted
  });

  it('Save includes api_key in payload when the user typed one', async () => {
    render(<SettingsPopover />);
    fireEvent.click(screen.getByRole('button', { name: /⚙/i }));
    await waitFor(() => expect(getConfig).toHaveBeenCalledTimes(1));

    const keyInput = screen.getByPlaceholderText(/leave blank/i);
    fireEvent.change(keyInput, { target: { value: 'sk-test-key' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(updateConfig).toHaveBeenCalledTimes(1));
    const payload = updateConfig.mock.calls[0][0];
    expect(payload.api_key).toBe('sk-test-key');
  });

  it('Reset button calls clearConfig and refreshes status', async () => {
    render(<SettingsPopover />);
    fireEvent.click(screen.getByRole('button', { name: /⚙/i }));
    await waitFor(() => expect(getConfig).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole('button', { name: /reset/i }));
    await waitFor(() => expect(clearConfig).toHaveBeenCalledTimes(1));
  });
});
