import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RightDock from './RightDock';

const chat = { transcript: [{ role: 'agent', text: 'hi there' }], proposal: null, sending: false,
  onSend: () => {}, onApply: () => {}, onReject: () => {}, onCancel: () => {} };
const SUMMARY = { components: [], knowledge_bases: [] };
const FINDINGS = [{ code: 'WIZ102', severity: 'error', message: 'orphan', id: 'n1' }];

function setup(tab = 'chat', onTabChange = vi.fn()) {
  render(<RightDock activeTab={tab} onTabChange={onTabChange} summary={SUMMARY}
    findings={FINDINGS} selectedNode={null} onSelectNode={() => {}} chat={chat} intents={[]} />);
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

describe('RightDock Intents tab', () => {
  const baseProps = {
    activeTab: 'intents', onTabChange: vi.fn(), summary: SUMMARY, findings: [],
    selectedNode: null, onSelectNode: () => {}, chat,
  };

  it('renders intents-panel when intents tab is active', () => {
    render(<RightDock {...baseProps} intents={[]} />);
    expect(screen.getByTestId('intents-panel')).toBeInTheDocument();
  });
});

describe('RightDock Tags tab', () => {
  const summaryWithTags = {
    components: [],
    knowledge_bases: [],
    tags: [
      {
        category: 'Sentiment',
        category_id: 'cat1',
        values: ['Positive', 'Negative'],
        node_count: 5,
      },
      {
        category: 'Type',
        category_id: 'cat2',
        values: ['Question'],
        node_count: 2,
      },
    ],
  };

  const baseProps = {
    activeTab: 'tags', onTabChange: vi.fn(), summary: summaryWithTags, findings: [],
    selectedNode: null, onSelectNode: () => {}, chat, intents: [],
  };

  it('renders tags-panel when tags tab is active', () => {
    render(<RightDock {...baseProps} />);
    expect(screen.getByTestId('tags-panel')).toBeInTheDocument();
  });

  it('displays tag categories and values', () => {
    render(<RightDock {...baseProps} />);
    expect(screen.getByText('Sentiment')).toBeInTheDocument();
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Positive')).toBeInTheDocument();
    expect(screen.getByText('Negative')).toBeInTheDocument();
    expect(screen.getByText('Question')).toBeInTheDocument();
    expect(screen.getByText('5 nodes')).toBeInTheDocument();
    expect(screen.getByText('2 nodes')).toBeInTheDocument();
  });

  it('shows empty state when no tags', () => {
    const emptyProps = {
      activeTab: 'tags', onTabChange: vi.fn(), summary: SUMMARY, findings: [],
      selectedNode: null, onSelectNode: () => {}, chat, intents: [],
    };
    render(<RightDock {...emptyProps} />);
    expect(screen.getByText('No tags.')).toBeInTheDocument();
  });
});

describe('RightDock KB tab', () => {
  const summaryWithKb = {
    components: [],
    knowledge_bases: [
      { knowledge_id: 1, title: 'Simple KB', intents: [5], intent_names: ['WantPay'],
        answers: [{ text: 'Hello', after: 'wait' }], trigger_type: 'intent',
        is_user_created: true, multi_round: null, multi_round_target: null },
    ],
    global_hot_words: [],
  };

  const baseProps = {
    activeTab: 'kb', onTabChange: vi.fn(), summary: summaryWithKb, findings: [],
    selectedNode: null, onSelectNode: () => {}, chat, focusKb: null,
  };

  it('shows list, drills into detail on row click, and returns on back', () => {
    render(<RightDock {...baseProps} />);
    expect(screen.getByTestId('kb-plane')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('kb-row'));
    expect(screen.getByTestId('kb-detail-panel')).toBeInTheDocument();
    expect(screen.getByText('Simple KB')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('kb-back'));
    expect(screen.getByTestId('kb-plane')).toBeInTheDocument();
  });

  it('opens detail for the focusKb id', () => {
    render(<RightDock {...baseProps} focusKb={{ id: 1, nonce: 1 }} />);
    expect(screen.getByTestId('kb-detail-panel')).toBeInTheDocument();
    expect(screen.getByText('Simple KB')).toBeInTheDocument();
  });
});
