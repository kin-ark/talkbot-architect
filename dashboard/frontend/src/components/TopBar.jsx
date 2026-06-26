import Button from './ui/Button';

export default function TopBar({ canUndo, canRedo, onUndo, onRedo, onExport, onNew }) {
  return (
    <div className="h-12 border-b border-border bg-surface flex items-center justify-between px-4">
      <span className="font-semibold text-text">Talkbot Architect</span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" onClick={onNew}>New / Upload</Button>
        <Button variant="secondary" onClick={onUndo} disabled={!canUndo}>Undo</Button>
        <Button variant="secondary" onClick={onRedo} disabled={!canRedo}>Redo</Button>
        <Button variant="secondary" onClick={onExport}>Export</Button>
      </div>
    </div>
  );
}
