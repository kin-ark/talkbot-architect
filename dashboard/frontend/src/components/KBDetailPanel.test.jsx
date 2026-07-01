import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import KBDetailPanel from './KBDetailPanel';

const simpleKb = {
  knowledge_id: 100, title: 'Payment KB', intents: [5, 6],
  intent_names: ['WantPay', 'Refuse'],
  answers: [{ text: 'Please pay now.', after: 'wait' }, { text: 'Goodbye.', after: 'hangup' }],
  trigger_type: 'intent', is_user_created: true, multi_round: null, multi_round_target: null,
};
const mrKb = {
  knowledge_id: 200, title: 'MR KB', intents: [], intent_names: [],
  answers: [], trigger_type: 'intent', is_user_created: true,
  multi_round: { components: [] }, multi_round_target: 'Collect Flow',
};

describe('KBDetailPanel', () => {
  it('renders title, intent-name chips and answers with after badges', () => {
    render(<KBDetailPanel kb={simpleKb} />);
    expect(screen.getByText('Payment KB')).toBeInTheDocument();
    expect(screen.getByText('WantPay')).toBeInTheDocument();
    expect(screen.getByText('Refuse')).toBeInTheDocument();
    expect(screen.getByText('Please pay now.')).toBeInTheDocument();
    expect(screen.getByText(/Hang up/i)).toBeInTheDocument();
    expect(screen.getByText(/Intent Trigger/i)).toBeInTheDocument();
  });

  it('shows drill button only for multi-round and fires onDrillIn', () => {
    const onDrillIn = vi.fn();
    const { rerender } = render(<KBDetailPanel kb={simpleKb} onDrillIn={onDrillIn} />);
    expect(screen.queryByTestId('kb-drill')).toBeNull();
    rerender(<KBDetailPanel kb={mrKb} onDrillIn={onDrillIn} />);
    const btn = screen.getByTestId('kb-drill');
    expect(screen.getByText('Collect Flow')).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onDrillIn).toHaveBeenCalledWith(mrKb);
  });

  it('falls back to numeric id when intent name is missing', () => {
    const kb = { ...simpleKb, intents: [5, 6], intent_names: ['WantPay', '6'] };
    render(<KBDetailPanel kb={kb} />);
    expect(screen.getByText('WantPay')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
  });
});
