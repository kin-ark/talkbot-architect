import { vi, describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
vi.mock('../api');
import * as api from '../api';
import SampleGallery from './SampleGallery';

beforeEach(() => vi.clearAllMocks());

describe('SampleGallery', () => {
  it('renders sample cards and fires onPick on click', async () => {
    api.listSamples.mockResolvedValue([
      { id: 'greeting_faq', title: 'Greeting & FAQ', description: 'minimal' },
      { id: 'debt_dpd1_5', title: 'Debt Collector', description: 'transfer' },
    ]);
    const onPick = vi.fn();
    render(<SampleGallery onPick={onPick} />);
    await waitFor(() => expect(screen.getByText('Greeting & FAQ')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Debt Collector'));
    expect(onPick).toHaveBeenCalledWith('debt_dpd1_5');
  });

  it('renders nothing when the list is empty', async () => {
    api.listSamples.mockResolvedValue([]);
    render(<SampleGallery onPick={() => {}} />);
    await waitFor(() => expect(api.listSamples).toHaveBeenCalled());
    expect(screen.queryByTestId('sample-gallery')).toBeNull();
  });

  it('groups debt vs starters and renders cards', async () => {
    api.listSamples.mockResolvedValue([
      { id: 'greeting_faq', title: 'Greeting', description: 'x' },
      { id: 'debt_dpd1_5', title: 'DPD1-5', description: 'y' },
    ]);
    render(<SampleGallery onPick={() => {}} />);
    expect(await screen.findByText('Debt Collection')).toBeInTheDocument();
    expect(screen.getByText('Starters')).toBeInTheDocument();
    expect(screen.getAllByTestId('sample-card')).toHaveLength(2);
  });
});
