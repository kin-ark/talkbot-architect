import { describe, it, expect } from 'vitest';
import { tokensFor, KNOWN_TOKENS, CANNED } from './recovery';

describe('tokensFor', () => {
  it('prefers an explicit recovery list, filtered to known tokens', () => {
    expect(tokensFor({ recovery: ['fix', 'discard', 'bogus'] })).toEqual(['fix', 'discard']);
  });
  it('maps stop_reason limit to continue', () => {
    expect(tokensFor({ stopReason: 'limit' })).toEqual(['continue']);
  });
  it('maps kinds without an explicit list', () => {
    expect(tokensFor({ kind: 'transient' })).toEqual(['retry']);
    expect(tokensFor({ kind: 'proposal_blocked' })).toEqual(['fix', 'discard']);
    expect(tokensFor({ kind: 'tool_arg' })).toEqual(['edit', 'retry']);
  });
  it('defaults to retry', () => {
    expect(tokensFor({})).toEqual(['retry']);
    expect(tokensFor({ kind: 'unknown' })).toEqual(['retry']);
  });
  it('exposes known tokens and canned prompts', () => {
    expect(KNOWN_TOKENS).toContain('continue');
    expect(CANNED.fix).toMatch(/re-propose/i);
  });
});
