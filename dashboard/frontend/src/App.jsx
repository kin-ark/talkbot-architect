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
  const [preview, setPreview] = useState(null);
  const onExport = () => window.open(exportUrl(), '_blank');
  const onNew = () => {
    setSelectedNode(null); setDockTab('chat'); setFocusComponentId(null); setPreview(null);
    s.reset();           // clears backend + session state -> returns to landing
  };

  const ownerComponentOf = (uuid) => {
    for (const c of s.summary?.components || []) {
      if (c.nodes && c.nodes[uuid]) return c.uuid;
    }
    return null;
  };

  const resolveNode = (node) => {
    if (!node?.uuid) return node;
    for (const c of s.summary?.components || []) {
      if (c.nodes?.[node.uuid]) return c.nodes[node.uuid];
    }
    return node;
  };

  const selectNode = (node) => {
    const resolved = resolveNode(node);
    setSelectedNode(resolved);
    setDockTab('properties');
    const owner = resolved?.uuid ? ownerComponentOf(resolved.uuid) : null;
    if (owner) setFocusComponentId(owner);
  };

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

  const onPreview = (proposal) => setPreview(
    proposal?.proposed_summary ? { summary: proposal.proposed_summary, changeSet: proposal.change_set } : null);
  const exitPreview = () => setPreview(null);
  const applyAndExit = () => { exitPreview(); return s.apply(); };
  const rejectAndExit = () => { exitPreview(); s.reject(); };

  const chat = {
    transcript: s.transcript, proposal: s.proposal, sending: s.sending,
    onSend: s.send, onRetry: s.retry, onApply: applyAndExit, onReject: rejectAndExit, onCancel: s.cancel,
    canUndo: s.canUndo, canRedo: s.canRedo, onUndo: s.undo, onRedo: s.redo,
  };

  return (
    <div className="h-screen flex flex-col bg-canvas">
      <TopBar canUndo={s.canUndo} canRedo={s.canRedo} onUndo={s.undo} onRedo={s.redo} onExport={onExport} onNew={onNew} />
      <div className="flex-1 flex overflow-hidden">
        <ComponentsRail summary={s.summary} selectedComponentId={focusComponentId}
          onSelectComponent={setFocusComponentId} />
        <div className="flex-1 min-w-0 flex flex-col">
          {preview && (
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs bg-warning-bg text-warning border-b border-warning">
              <span>Previewing proposed change — added/changed nodes highlighted.</span>
              <button type="button" onClick={exitPreview}
                className="ml-auto text-primary hover:underline">Exit preview</button>
            </div>
          )}
          <div className="flex-1 min-h-0">
            <FlowCanvas summary={preview ? preview.summary : s.summary}
              onSelectNode={selectNode} focusComponentId={focusComponentId}
              highlight={preview ? preview.changeSet : null} />
          </div>
        </div>
        <RightDock activeTab={dockTab} onTabChange={setDockTab} summary={s.summary} findings={s.findings}
          selectedNode={selectedNode} onSelectNode={selectNode} chat={chat} onPreview={onPreview} />
      </div>
    </div>
  );
}
