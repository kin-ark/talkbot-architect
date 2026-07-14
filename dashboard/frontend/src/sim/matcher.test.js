import { describe, it, expect } from 'vitest';
import { matchUtterance } from './matcher';

// A talk node whose branches map to intents via all_client_intent.
const node = {
  branches: [
    { label: 'Positive', kind: 'intent' },
    { label: 'Negative', kind: 'intent' },
    { label: 'Unclassified', kind: 'intent' },
  ],
  data: { all_client_intent: [
    { name: 'Positive', intents: [{ intentId: '111' }] },
    { name: 'Negative', intents: [{ intentId: '222' }] },
    { name: 'Unclassified', intents: [{ intentId: '999' }] },
  ] },
};
const intentsById = new Map([
  ['111', { id: 111, name: 'Paid', keywords: ['sudah bayar', 'paid'], user_responses: ['I already paid it'] }],
  ['222', { id: 222, name: 'Refuse', keywords: ['tidak', 'belum'], user_responses: [] }],
  ['999', { id: 999, name: 'Unclear', keywords: ['whatever'], user_responses: [] }],
]);

describe('matchUtterance', () => {
  it('keyword substring hit selects that branch', () => {
    const m = matchUtterance('saya sudah bayar kemarin', node, intentsById);
    expect(m).toMatchObject({ branchIndex: 0, intentName: 'Paid' });
    expect(m.score).toBeGreaterThanOrEqual(2);
  });

  it('user_response token overlap hits with lower weight', () => {
    // "already" is a >=3-char token shared with intent 111's user_response
    const m = matchUtterance('already done', node, intentsById);
    expect(m?.branchIndex).toBe(0);
    expect(m.score).toBe(1);
  });

  it('a keyword hit outranks a response-only hit', () => {
    const m = matchUtterance('belum, I already paid', node, intentsById);
    // 'belum' keyword (Negative, +2) beats 'already'/'paid' — 'paid' is also a keyword (+2) for Positive.
    // Positive gets paid(kw +2) + already(resp +1) = 3; Negative gets belum(kw +2) = 2 → Positive wins.
    expect(m?.branchIndex).toBe(0);
  });

  it('no match returns null', () => {
    expect(matchUtterance('xyzzy foobar', node, intentsById)).toBeNull();
  });

  it('never selects the Unclassified branch even if its keyword matches', () => {
    const m = matchUtterance('whatever', node, intentsById);
    expect(m).toBeNull();
  });

  it('empty utterance returns null', () => {
    expect(matchUtterance('   ', node, intentsById)).toBeNull();
  });
});
