import SettingsPopover from './SettingsPopover';
import { useTheme } from '../theme/useTheme';

function Btn({ onClick, disabled, children }) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="px-3 py-1 text-sm rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50">{children}</button>
  );
}

export default function TopBar({ canUndo, canRedo, onUndo, onRedo, onExport, onNew }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="h-12 border-b border-slate-200 bg-white flex items-center justify-between px-4">
      <span className="font-semibold text-slate-700">Talkbot Architect</span>
      <div className="flex items-center gap-2">
        <Btn onClick={onNew}>New / Upload</Btn>
        <Btn onClick={onUndo} disabled={!canUndo}>Undo</Btn>
        <Btn onClick={onRedo} disabled={!canRedo}>Redo</Btn>
        <Btn onClick={onExport}>Export</Btn>
        <button onClick={toggle} aria-label="Toggle theme" title="Toggle light/dark"
          className="px-2 py-1 text-sm rounded border border-slate-200 hover:bg-slate-50">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        <SettingsPopover />
      </div>
    </div>
  );
}
