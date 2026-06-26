import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
beforeEach(() => { /* jsdom: no layout; we assert element presence, not pixels */ });
import ChatPane from './ChatPane';

const base = { proposal: null, onSend: () => {}, onApply: () => {}, onReject: () => {},
  onCancel: () => {}, summary: { components: [], knowledge_bases: [] } };

describe('ChatPane streaming', () => {
  it('shows a caret on the last agent bubble while sending', () => {
    const { getByTestId } = render(
      <ChatPane {...base} sending={true}
        transcript={[{ role: 'user', text: 'hi' }, { role: 'agent', text: 'Hel' }]} />);
    expect(getByTestId('stream-caret')).toBeInTheDocument();
  });

  it('no caret when not sending', () => {
    const { queryByTestId } = render(
      <ChatPane {...base} sending={false}
        transcript={[{ role: 'agent', text: 'done' }]} />);
    expect(queryByTestId('stream-caret')).not.toBeInTheDocument();
  });

  it('thinking bubble only before the agent bubble exists', () => {
    // last entry is user → still waiting → thinking shows
    const a = render(<ChatPane {...base} sending={true} transcript={[{ role: 'user', text: 'hi' }]} />);
    expect(a.queryByTestId('thinking')).toBeInTheDocument();
    a.unmount();   // both renders share document.body; clear the first before asserting absence
    // last entry is the streaming agent bubble → caret instead of thinking
    const b = render(<ChatPane {...base} sending={true}
      transcript={[{ role: 'user', text: 'hi' }, { role: 'agent', text: 'Hel' }]} />);
    expect(b.queryByTestId('thinking')).not.toBeInTheDocument();
  });
});
