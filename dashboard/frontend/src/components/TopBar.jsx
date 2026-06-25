import SettingsPopover from './SettingsPopover';
import { useTheme } from '../theme/useTheme';
import Button from './ui/Button';

export default function TopBar({ canUndo, canRedo, onUndo, onRedo, onExport, onNew }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="h-12 border-b border-border bg-surface flex items-center justify-between px-4">
      <span className="font-semibold text-text">Talkbot Architect</span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" onClick={onNew}>New / Upload</Button>
        <Button variant="secondary" onClick={onUndo} disabled={!canUndo}>Undo</Button>
        <Button variant="secondary" onClick={onRedo} disabled={!canRedo}>Redo</Button>
        <Button variant="secondary" onClick={onExport}>Export</Button>
        <button onClick={toggle} aria-label="Toggle theme" title="Toggle light/dark"
          className="px-2 py-1 text-sm rounded border border-border hover:bg-surface-muted">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        <SettingsPopover />
      </div>
    </div>
  );
}
