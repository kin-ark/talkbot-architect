import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPane from './ChatPane';

const base = { transcript: [], proposal: null, sending: false, onSend: () => {}, onApply: () => {},
  onReject: () => {}, onCancel: () => {}, onRetry: () => {}, summary: { components: [], knowledge_bases: [] } };

describe('ChatPane undo/redo', () => {
  it('Undo disabled when canUndo is false', () => {
    render(<ChatPane {...base} canUndo={false} canRedo={false} onUndo={() => {}} onRedo={() => {}} />);
    expect(screen.getByRole('button', { name: /undo/i })).toBeDisabled();
  });
  it('Undo calls onUndo when enabled', () => {
    const onUndo = vi.fn();
    render(<ChatPane {...base} canUndo={true} canRedo={false} onUndo={onUndo} onRedo={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /undo/i }));
    expect(onUndo).toHaveBeenCalled();
  });
});
