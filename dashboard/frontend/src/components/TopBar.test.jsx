import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import TopBar from './TopBar';

const base = { canUndo: false, canRedo: true, onUndo: () => {}, onRedo: () => {}, onExport: () => {}, onNew: () => {} };

describe('TopBar', () => {
  it('disables undo when canUndo is false and fires onExport', () => {
    const onExport = vi.fn();
    render(<TopBar {...base} onExport={onExport} />);
    expect(screen.getByText('Undo').closest('button')).toBeDisabled();
    fireEvent.click(screen.getByText('Export'));
    expect(onExport).toHaveBeenCalled();
  });

  it('renders the bot name', () => {
    render(<TopBar {...base} botName="Debt Collector" onRenameBot={() => {}} />);
    expect(screen.getByTestId('bot-name').textContent).toMatch(/Debt Collector/);
  });

  it('shows "Untitled bot" placeholder for null or "Empty Dialogue"', () => {
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
});
