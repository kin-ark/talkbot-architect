import { describe, it, expect } from 'vitest';
import { narrate, NARRATION } from './narration';

describe('narrate', () => {
  it('maps known tool names to present-continuous phrases', () => {
    expect(narrate('validate')).toBe('Checking the dialogue');
    expect(narrate('add_node')).toBe('Adding a node');
    expect(NARRATION.build).toBe('Building from manifest');
  });
  it('humanizes an unmapped tool name', () => {
    expect(narrate('foo_bar')).toBe('foo bar');
  });
  it('handles null/undefined safely', () => {
    expect(narrate(null)).toBe('');
    expect(narrate(undefined)).toBe('');
  });
});
