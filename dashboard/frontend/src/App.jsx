import { useState } from 'react';
import { useSession } from './state/useSession';
import TopBar from './components/TopBar';
import ChatPane from './components/ChatPane';
import SidePanel from './components/SidePanel';
import UploadZone from './components/UploadZone';
import SettingsPopover from './components/SettingsPopover';
import { exportUrl } from './api';

export default function App() {
  const s = useSession();
  const [selectedNode, setSelectedNode] = useState(null);
  const onExport = () => window.open(exportUrl(), '_blank');
  const onNew = () => window.location.reload();

  if (!s.summary) {
    return (
      <div className="h-screen flex flex-col bg-canvas">
        <div className="flex justify-end p-3">
          <SettingsPopover />
        </div>
        <div className="flex-1 flex items-center justify-center -mt-12">
          <div className="max-w-md w-full">
            <h2 className="text-2xl font-semibold mb-4 text-center text-text">Talkbot Architect</h2>
            <p className="text-center text-text-secondary mb-6 text-sm">Upload a WIZ dialogue JSON or ZIP to begin.</p>
            <UploadZone onUpload={s.upload} />
            <button onClick={s.startBlank}
              className="mt-4 w-full border border-border rounded-xl py-2 text-sm text-text-secondary hover:bg-surface-muted">
              Start from scratch — describe a new bot
            </button>
            {s.loading && <p className="text-center mt-4 text-text-tertiary">Analyzing…</p>}
            <p className="text-center mt-6 text-xs text-text-tertiary">Set your AI provider/key via ⚙ (top-right) or a backend <code>.env</code>.</p>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="h-screen flex flex-col bg-canvas">
      <TopBar canUndo={s.canUndo} canRedo={s.canRedo} onUndo={s.undo} onRedo={s.redo} onExport={onExport} onNew={onNew} />
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 min-w-0">
          <ChatPane transcript={s.transcript} proposal={s.proposal} sending={s.sending}
            onSend={s.send} onApply={s.apply} onReject={s.reject} onCancel={s.cancel} />
        </div>
        <SidePanel summary={s.summary} findings={s.findings} selectedNode={selectedNode} onSelectNode={setSelectedNode} />
      </div>
    </div>
  );
}
