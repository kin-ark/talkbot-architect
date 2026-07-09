import { describe, it, expect } from 'vitest';
import { classifyError } from './errorInfo';

describe('classifyError', () => {
  it('detects auth errors and keeps the raw detail', () => {
    const raw = "Error code: 401 - {'type':'error','error':{'type':'authentication_error','message':'invalid x-api-key'}}";
    const r = classifyError(raw);
    expect(r.title).toBe('Authentication failed');
    expect(r.hint).toMatch(/Settings/);
    expect(r.detail).toBe(raw);
  });

  it('detects rate limits', () => {
    expect(classifyError('Error code: 429 rate_limit_error').title).toBe('Rate limited');
  });

  it('detects overloaded / no-accounts', () => {
    expect(classifyError('529 overloaded_error').title).toBe('Model overloaded');
    expect(classifyError('No available accounts in group other').title).toBe('Model overloaded');
  });

  it('detects connection problems', () => {
    expect(classifyError('Connection error.').title).toBe('Connection problem');
  });

  it('detects context-length overflow', () => {
    expect(classifyError('prompt is too long: 250000 tokens').title).toBe('Conversation too long');
  });

  it('detects the vision-model message', () => {
    expect(classifyError("the current model can't read images; pick a Claude vision model")
      .title).toBe("Model can't read images");
  });

  it('falls back for unknown errors and never returns empty detail', () => {
    const r = classifyError('');
    expect(r.title).toBe('Something went wrong');
    expect(r.hint).toBeNull();
    expect(r.detail).toBe('Request failed.');
  });

  it('tolerates null/undefined input', () => {
    expect(classifyError(null).title).toBe('Something went wrong');
    expect(classifyError(undefined).detail).toBe('Request failed.');
  });
});
