import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RightDock from './RightDock';

const chat = { transcript: [{ role: 'agent', text: 'hi there' }], proposal: null, sending: false,
  onSend: () => {}, onApply: () => {}, onReject: () => {}, onCancel: () => {} };
const SUMMARY = { components: [], knowledge_bases: [] };
const FINDINGS = [{ code: 'WIZ102', severity: 'error', message: 'orphan', id: 'n1' }];

function setup(tab = 'chat', onTabChange = vi.fn()) {
  render(<RightDock activeTab={tab} onTabChange={onTabChange} summary={SUMMARY}
    findings={FINDINGS} selectedNode={null} onSelectNode={() => {}} chat={chat} />);
  return { onTabChange };
}

describe('RightDock', () => {
  it('shows Chat content on the chat tab', () => {
    setup('chat');
    expect(screen.getByText('hi there')).toBeInTheDocument();
  });
  it('clicking the Findings tab fires onTabChange("findings")', () => {
    const { onTabChange } = setup('chat');
    fireEvent.click(screen.getByText('Findings'));
    expect(onTabChange).toHaveBeenCalledWith('findings');
  });
  it('findings tab renders the finding', () => {
    setup('findings');
    expect(screen.getByText(/WIZ102/)).toBeInTheDocument();
  });
});
