import { useState, useEffect, useCallback } from 'react';
import { useSession } from './state/useSession';
import { useConfirm } from './confirm/ConfirmProvider';
import TopBar from './components/TopBar';
import SessionRail from './components/SessionRail';
import FlowCanvas from './components/FlowCanvas';
import RightDock from './components/RightDock';
import EmptyState from './components/EmptyState';
import FlowSkeleton from './components/FlowSkeleton';
import PageOverlay from './components/PageOverlay';
import StatisticsPage from './components/StatisticsPage';
import DocsPage from './components/DocsPage';
import SettingsPage from './components/SettingsPage';
import { useTheme } from './theme/useTheme';
import { exportUrl, componentExportUrl, getConfig, getModels } from './api';

export default function App() {
  const s = useSession();
  const confirm = useConfirm();
  const [selectedNode, setSelectedNode] = useState(null);
  const [dockTab, setDockTab] = useState('chat');
  const [focusComponentId, setFocusComponentId] = useState(null);
  const [focusKb, setFocusKb] = useState(null);
  const [preview, setPreview] = useState(null);
  const [simNode, setSimNode] = useState(null);
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
  const [models, setModels] = useState([]);
  const [config, setConfig] = useState(null);
  const [customId, setCustomId] = useState('');
  // Load config+models on mount (NOT gated on empty-state) so a rehydrated
  // session on reload still knows the model's vision capability -> image input
  // works. Also called after a Settings save so canSendImages stays fresh.
  const loadConfig = useCallback(() => {
    return Promise.all([getConfig(), getModels()])
      .then(([c, m]) => {
        setKeySet(!!c.key_set);
        setConfig(c);
        setModels(m.models || []);
        setCustomId(m.custom_id || '');
      })
      .catch(() => {});
  }, []);
  useEffect(() => { loadConfig(); }, [loadConfig]);

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
      {leftPage === 'settings' && <SettingsPage onSaved={loadConfig} />}
    </PageOverlay>
  );

  const canSendImages = (() => {
    if (!config) return false;
    const modelId = config.model_id;
    if (!modelId) return false;
    if (modelId === customId) {
      return config.custom_vision === true;
    }
    const model = models.find((m) => m.id === modelId);
    return model?.vision === true;
  })();

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
        botName={s.botName} onRenameBot={s.renameBot} isComponent={s.isComponent} onExportComponent={onExportComponent} componentWarnings={s.componentWarnings} />
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
                  simCurrentNode={simNode}
                  onSelectKb={(id) => { setDockTab('kb'); setFocusKb((f) => ({ id, nonce: (f?.nonce || 0) + 1 })); }} />
              </div>
            </>
          ) : (s.loading && !s.uploadProgress) ? (
            <FlowSkeleton />
          ) : (
            <EmptyState keySet={keySet} loading={s.loading} uploadProgress={s.uploadProgress}
              onUpload={s.upload} onStartBlank={s.startBlank} onLoadSample={s.loadSample}
              onOpenSettings={() => setLeftPage('settings')} />
          )}
        </div>
        {(s.summary || s.activeSessionId) && (
          <RightDock activeTab={dockTab} onTabChange={setDockTab} summary={s.summary} findings={s.findings}
            selectedNode={selectedNode ? resolveNode(selectedNode) : null} onSelectNode={selectNode} chat={chat}
            onPreview={onPreview} onAskFix={onAskFix}
            onSelectComponent={setFocusComponentId} focusComponentId={focusComponentId}
            onEditNode={(uuid, fields) => s.editNodeText(uuid, fields)}
            intents={s.intents} focusKb={focusKb} onExportComponent={s.isComponent ? undefined : onExportComponent}
            canSendImages={canSendImages} onSimNode={setSimNode} />
        )}
      </div>
      {pageOverlay}
    </div>
  );
}
