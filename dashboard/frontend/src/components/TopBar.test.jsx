import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import TopBar from './TopBar';

const base = { hasDoc: true, canUndo: false, canRedo: true, onUndo: () => {}, onRedo: () => {}, onExport: () => {}, isComponent: false };

describe('TopBar', () => {
  it('renders iconified undo/redo and no New button', () => {
    render(<TopBar {...base} />);
    expect(screen.getByLabelText('Undo')).toBeInTheDocument();
    expect(screen.getByLabelText('Redo')).toBeInTheDocument();
    expect(screen.queryByText('New / Upload')).toBeNull();
  });

  it('disables undo when canUndo is false and fires onExport', () => {
    const onExport = vi.fn();
    render(<TopBar {...base} onExport={onExport} />);
    expect(screen.getByLabelText('Undo')).toBeDisabled();
    fireEvent.click(screen.getByText('Export'));
    expect(onExport).toHaveBeenCalled();
  });

  it('greys all doc-actions when hasDoc is false (even if canUndo/canRedo true)', () => {
    render(<TopBar {...base} hasDoc={false} canUndo canRedo />);
    expect(screen.getByLabelText('Undo')).toBeDisabled();
    expect(screen.getByLabelText('Redo')).toBeDisabled();
    expect(screen.getByText('Export').closest('button')).toBeDisabled();
  });

  it('shows the "Talkbot Architect" placeholder (non-editable) when hasDoc is false', () => {
    render(<TopBar {...base} hasDoc={false} botName={null} onRenameBot={() => {}} />);
    expect(screen.getByTestId('bot-name').textContent).toMatch(/Talkbot Architect/);
    fireEvent.click(screen.getByTestId('bot-name'));
    expect(screen.queryByTestId('bot-name-input')).toBeNull();   // not editable on empty
  });

  it('renders the bot name when hasDoc', () => {
    render(<TopBar {...base} botName="Debt Collector" onRenameBot={() => {}} />);
    expect(screen.getByTestId('bot-name').textContent).toMatch(/Debt Collector/);
  });

  it('shows "Untitled bot" placeholder for null or "Empty Dialogue" when hasDoc', () => {
    const { rerender } = render(<TopBar {...base} botName={null} onRenameBot={() => {}} />);
    expect(screen.getByTestId('bot-name').textContent).toMatch(/Untitled bot/);
    rerender(<TopBar {...base} botName="Empty Dialogue" onRenameBot={() => {}} />);
    expect(screen.getByTestId('bot-name').textContent).toMatch(/Untitled bot/);
  });

  it('editing the name and pressing Enter fires onRenameBot', () => {
    const onRenameBot = vi.fn();
    render(<TopBar {...base} botName="Old" onRenameBot={onRenameBot} />);
    fireEvent.click(screen.getByTestId('bot-name'));
    const input = screen.getByTestId('bot-name-input');
    fireEvent.change(input, { target: { value: 'New Name' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onRenameBot).toHaveBeenCalledWith('New Name');
  });

  it('pressing Escape in the name input cancels edit without committing', () => {
    const onRenameBot = vi.fn();
    render(<TopBar {...base} botName="Old" onRenameBot={onRenameBot} />);
    fireEvent.click(screen.getByTestId('bot-name'));
    const input = screen.getByTestId('bot-name-input');
    fireEvent.change(input, { target: { value: 'Changed' } });
    fireEvent.keyDown(input, { key: 'Escape' });
    fireEvent.blur(input);
    expect(onRenameBot).not.toHaveBeenCalled();
  });

  it('shows a Component badge when isComponent', () => {
    render(<TopBar {...base} isComponent botName="Widget" />);
    expect(screen.getByTestId('component-badge')).toBeInTheDocument();
  });

  it('no Component badge for a full bot', () => {
    render(<TopBar {...base} isComponent={false} botName="Bot" />);
    expect(screen.queryByTestId('component-badge')).toBeNull();
  });
});
