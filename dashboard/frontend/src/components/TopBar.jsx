import React from 'react';
import SettingsPopover from './SettingsPopover';

export default function TopBar({ canUndo, canRedo, onUndo, onRedo, onExport, onNew }) {
  const Btn = ({ onClick, disabled, children }) => (
    <button onClick={onClick} disabled={disabled}
      className="px-3 py-1 text-sm rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50">{children}</button>
  );
  return (
    <div className="h-12 border-b border-slate-200 bg-white flex items-center justify-between px-4">
      <span className="font-semibold text-slate-700">Talkbot Architect</span>
      <div className="flex items-center gap-2">
        <Btn onClick={onNew}>New / Upload</Btn>
        <Btn onClick={onUndo} disabled={!canUndo}>Undo</Btn>
        <Btn onClick={onRedo} disabled={!canRedo}>Redo</Btn>
        <Btn onClick={onExport}>Export</Btn>
        <SettingsPopover />
      </div>
    </div>
  );
}
