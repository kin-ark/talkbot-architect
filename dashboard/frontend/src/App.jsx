import { useState } from 'react';
import { useSession } from './state/useSession';
import TopBar from './components/TopBar';
import ComponentsRail from './components/ComponentsRail';
import FlowCanvas from './components/FlowCanvas';
import RightDock from './components/RightDock';
import UploadZone from './components/UploadZone';
import SettingsPopover from './components/SettingsPopover';
import { exportUrl } from './api';

export default function App() {
  const s = useSession();
  const [selectedNode, setSelectedNode] = useState(null);
  const [dockTab, setDockTab] = useState('chat');
  const [focusComponentId, setFocusComponentId] = useState(null);
  const onExport = () => window.open(exportUrl(), '_blank');
  const onNew = () => window.location.reload();

  const selectNode = (node) => { setSelectedNode(node); setDockTab('properties'); };

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

  const chat = {
    transcript: s.transcript, proposal: s.proposal, sending: s.sending,
    onSend: s.send, onApply: s.apply, onReject: s.reject, onCancel: s.cancel,
  };

  return (
    <div className="h-screen flex flex-col bg-canvas">
      <TopBar canUndo={s.canUndo} canRedo={s.canRedo} onUndo={s.undo} onRedo={s.redo} onExport={onExport} onNew={onNew} />
      <div className="flex-1 flex overflow-hidden">
        <ComponentsRail summary={s.summary} selectedComponentId={focusComponentId}
          onSelectComponent={setFocusComponentId}
          onAddComponent={() => setDockTab('chat')} />
        <div className="flex-1 min-w-0">
          <FlowCanvas summary={s.summary} onSelectNode={selectNode} focusComponentId={focusComponentId} />
        </div>
        <RightDock activeTab={dockTab} onTabChange={setDockTab} summary={s.summary} findings={s.findings}
          selectedNode={selectedNode} onSelectNode={selectNode} chat={chat} />
      </div>
    </div>
  );
}
