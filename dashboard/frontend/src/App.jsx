import { useState, useEffect } from 'react';
import { useSession } from './state/useSession';
import { useConfirm } from './confirm/ConfirmProvider';
import TopBar from './components/TopBar';
import SessionRail from './components/SessionRail';
import FlowCanvas from './components/FlowCanvas';
import RightDock from './components/RightDock';
import EmptyState from './components/EmptyState';
import PageOverlay from './components/PageOverlay';
import StatisticsPage from './components/StatisticsPage';
import DocsPage from './components/DocsPage';
import SettingsPage from './components/SettingsPage';
import { useTheme } from './theme/useTheme';
import { exportUrl, componentExportUrl, getConfig } from './api';
import { toast } from './toast/toastStore';

export default function App() {
  const s = useSession();
  const confirm = useConfirm();
  const [selectedNode, setSelectedNode] = useState(null);
  const [dockTab, setDockTab] = useState('chat');
  const [focusComponentId, setFocusComponentId] = useState(null);
  const [focusKb, setFocusKb] = useState(null);
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
    if (s.summary) return;                       // only probe on the empty state
    let off = false;
    getConfig().then((c) => { if (!off) setKeySet(!!c.key_set); }).catch(() => {});
    return () => { off = true; };
  }, [s.summary]);

  const onExport = async () => {
    const errs = s.findings.filter((f) => f.severity === 'error').length;
    if (errs > 0) {
      const ok = await confirm({
        title: 'Export with errors?',
        message: `${errs} error${errs > 1 ? 's' : ''} found — export anyway?`,
        confirmLabel: 'Export anyway',
      });
      if (!ok) return;
    }
    window.open(exportUrl(), '_blank');
  };

  const onExportComponent = (uuid) => {
    const kbs = s.summary?.knowledge_bases?.length || 0;
    if (kbs) toast.info(`${kbs} knowledge base${kbs === 1 ? '' : 's'} won't be included in the component export`);
    window.open(componentExportUrl(uuid), '_blank');
  };

  const onStartNew = () => {
    setSelectedNode(null); setDockTab('chat'); setFocusComponentId(null); setPreview(null);
    s.startNew();          // empty-state center; keeps backend + session list
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

  const PAGE_TITLES = { stats: 'Statistics', settings: 'Settings' };
  const pageOverlay = leftPage && leftPage !== 'docs' && (
    <PageOverlay title={PAGE_TITLES[leftPage]} onClose={() => setLeftPage(null)}>
      {leftPage === 'stats' && (
        <StatisticsPage usage={s.usage} sessions={s.sessions} activeSessionId={s.activeSessionId} />
      )}
      {leftPage === 'settings' && <SettingsPage />}
    </PageOverlay>
  );

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

  if (leftPage === 'docs') {
    return <DocsPage onClose={() => setLeftPage(null)} />;
  }

  return (
    <div className="h-screen flex flex-col bg-canvas">
      <TopBar hasDoc={!!s.summary} canUndo={s.canUndo} canRedo={s.canRedo}
        onUndo={s.undo} onRedo={s.redo} onExport={onExport}
        botName={s.botName} onRenameBot={s.renameBot} isComponent={s.isComponent} onExportComponent={onExportComponent} />
      <div className="flex-1 flex overflow-hidden">
        <SessionRail sessions={s.sessions} activeSessionId={s.activeSessionId}
          usage={s.usage} collapsed={railCollapsed} onToggleCollapse={toggleRail}
          onNew={onStartNew} onSwitch={s.switchSession}
          onRename={s.renameSession} onDelete={s.deleteSession}
          onOpenPage={setLeftPage} theme={theme} onToggleTheme={toggleTheme} />
        <div className="flex-1 min-w-0 flex flex-col">
          {s.summary ? (
            <>
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
                  highlight={preview ? preview.changeSet : null}
                  onSelectKb={(id) => { setDockTab('kb'); setFocusKb((f) => ({ id, nonce: (f?.nonce || 0) + 1 })); }} />
              </div>
            </>
          ) : (
            <EmptyState keySet={keySet} loading={s.loading}
              onUpload={s.upload} onStartBlank={s.startBlank} onLoadSample={s.loadSample}
              onOpenSettings={() => setLeftPage('settings')} />
          )}
        </div>
        {s.summary && (
          <RightDock activeTab={dockTab} onTabChange={setDockTab} summary={s.summary} findings={s.findings}
            selectedNode={selectedNode ? resolveNode(selectedNode) : null} onSelectNode={selectNode} chat={chat}
            onPreview={onPreview} onAskFix={onAskFix}
            onSelectComponent={setFocusComponentId} focusComponentId={focusComponentId}
            onEditNode={(uuid, fields) => s.editNodeText(uuid, fields)}
            intents={s.intents} focusKb={focusKb} onExportComponent={s.isComponent ? undefined : onExportComponent} />
        )}
      </div>
      {pageOverlay}
    </div>
  );
}
