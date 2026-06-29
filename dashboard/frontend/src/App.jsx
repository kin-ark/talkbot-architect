import { useState, useEffect } from 'react';
import { useSession } from './state/useSession';
import TopBar from './components/TopBar';
import SessionRail from './components/SessionRail';
import FlowCanvas from './components/FlowCanvas';
import RightDock from './components/RightDock';
import UploadZone from './components/UploadZone';
import PageOverlay from './components/PageOverlay';
import StatisticsPage from './components/StatisticsPage';
import DocumentationPage from './components/DocumentationPage';
import SettingsPage from './components/SettingsPage';
import WelcomeCard from './components/WelcomeCard';
import SampleGallery from './components/SampleGallery';
import { Settings as SettingsIcon, Sun, Moon } from 'lucide-react';
import { useTheme } from './theme/useTheme';
import { exportUrl, getConfig } from './api';

export default function App() {
  const s = useSession();
  const [selectedNode, setSelectedNode] = useState(null);
  const [dockTab, setDockTab] = useState('chat');
  const [focusComponentId, setFocusComponentId] = useState(null);
  const [preview, setPreview] = useState(null);
  const [railCollapsed, setRailCollapsed] = useState(() => {
    try { return localStorage.getItem('tb-rail-collapsed') === '1'; } catch { return false; }
  });
  const toggleRail = () => setRailCollapsed((c) => {
    const next = !c;
    try { localStorage.setItem('tb-rail-collapsed', next ? '1' : '0'); } catch { /* ignore */ }
    return next;
  });
  const [leftPage, setLeftPage] = useState(null);
  const { theme, toggle: toggleTheme } = useTheme();
  const [keySet, setKeySet] = useState(true);   // assume set until known (no false flash)
  useEffect(() => {
    if (s.summary) return;                       // only probe on the landing screen
    let off = false;
    getConfig().then((c) => { if (!off) setKeySet(!!c.key_set); }).catch(() => {});
    return () => { off = true; };
  }, [s.summary]);
  const onExport = () => {
    const errs = s.findings.filter((f) => f.severity === 'error').length;
    if (errs > 0 && !window.confirm(`${errs} error${errs > 1 ? 's' : ''} found — export anyway?`)) return;
    window.open(exportUrl(), '_blank');
  };
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

  const PAGE_TITLES = { stats: 'Statistics', docs: 'Documentation', settings: 'Settings' };
  const pageOverlay = leftPage && (
    <PageOverlay title={PAGE_TITLES[leftPage]} onClose={() => setLeftPage(null)}>
      {leftPage === 'stats' && (
        <StatisticsPage usage={s.usage} sessions={s.sessions} activeSessionId={s.activeSessionId} />
      )}
      {leftPage === 'docs' && <DocumentationPage />}
      {leftPage === 'settings' && <SettingsPage />}
    </PageOverlay>
  );

  const landingControls = (
    <div className="flex items-center gap-1">
      <button type="button" aria-label="Toggle theme" title="Toggle light/dark" onClick={toggleTheme}
        className="p-2 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text">
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>
      <button type="button" aria-label="Settings" title="Settings" onClick={() => setLeftPage('settings')}
        className="p-2 rounded-md text-text-secondary hover:bg-surface-muted hover:text-text">
        <SettingsIcon size={16} />
      </button>
    </div>
  );

  if (!s.summary) {
    const uploadCard = (
      <div className="flex-1 flex items-center justify-center -mt-12">
        <div className="max-w-md w-full">
          <WelcomeCard />
          {!keySet && (
            <div data-testid="key-nudge" className="mb-4 rounded-lg border border-warning bg-warning-bg text-warning px-3 py-2 text-xs flex items-center gap-2">
              <span>No AI key set — the chat agent needs one.</span>
              <button type="button" onClick={() => setLeftPage('settings')}
                className="ml-auto text-primary hover:underline">Open Settings</button>
            </div>
          )}
          <h2 className="text-2xl font-semibold mb-4 text-center text-text">Talkbot Architect</h2>
          <p className="text-center text-text-secondary mb-6 text-sm">Upload a WIZ dialogue JSON or ZIP to begin.</p>
          <UploadZone onUpload={s.upload} />
          <button onClick={s.startBlank}
            className="mt-4 w-full border border-border rounded-xl py-2 text-sm text-text-secondary hover:bg-surface-muted">
            Start from scratch — describe a new bot
          </button>
          {s.loading && <p className="text-center mt-4 text-text-tertiary">Analyzing…</p>}
          <SampleGallery onPick={s.loadSample} />
        </div>
      </div>
    );

    if (s.sessions?.length > 0) {
      return (
        <div className="h-screen flex flex-col bg-canvas">
          <div className="flex justify-end p-3">
            {landingControls}
          </div>
          <div className="flex-1 flex overflow-hidden">
            <SessionRail sessions={s.sessions} activeSessionId={s.activeSessionId}
              usage={s.usage} collapsed={railCollapsed} onToggleCollapse={toggleRail}
              onNew={s.newSession} onSwitch={s.switchSession}
              onRename={s.renameSession} onDelete={s.deleteSession}
              onOpenPage={setLeftPage} theme={theme} onToggleTheme={toggleTheme} />
            {uploadCard}
          </div>
          {pageOverlay}
        </div>
      );
    }

    return (
      <div className="h-screen flex flex-col bg-canvas">
        <div className="flex justify-end p-3">
          {landingControls}
        </div>
        {uploadCard}
        {pageOverlay}
      </div>
    );
  }

  const onAskFix = (f) => {
    setDockTab('chat');
    s.send(`Fix finding ${f.code}${f.id ? ' on node ' + f.id : ''}: ${f.message}`);
  };
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
      <TopBar canUndo={s.canUndo} canRedo={s.canRedo} onUndo={s.undo} onRedo={s.redo} onExport={onExport} onNew={onNew}
        botName={s.botName} onRenameBot={s.renameBot} />
      <div className="flex-1 flex overflow-hidden">
        <SessionRail sessions={s.sessions} activeSessionId={s.activeSessionId}
          usage={s.usage} collapsed={railCollapsed} onToggleCollapse={toggleRail}
          onNew={s.newSession} onSwitch={s.switchSession}
          onRename={s.renameSession} onDelete={s.deleteSession}
          onOpenPage={setLeftPage} theme={theme} onToggleTheme={toggleTheme} />
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
          selectedNode={selectedNode ? resolveNode(selectedNode) : null} onSelectNode={selectNode} chat={chat} onPreview={onPreview} onAskFix={onAskFix}
          onSelectComponent={setFocusComponentId} focusComponentId={focusComponentId}
          onEditNode={(uuid, fields) => s.editNodeText(uuid, fields)} />
      </div>
      {pageOverlay}
    </div>
  );
}
