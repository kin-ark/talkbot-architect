import { useState, useEffect } from 'react';
import Tabs from './ui/Tabs';
import ChatPane from './ChatPane';
import FindingList from './FindingList';
import NodePropertiesPanel from './NodePropertiesPanel';
import KBPlane from './KBPlane';
import KBDetailPanel from './KBDetailPanel';
import IntentsPanel from './IntentsPanel';
import TagsPanel from './TagsPanel';
import FlowCanvas from './FlowCanvas';
import ComponentsRail from './ComponentsRail';
import SimulatorPanel from './SimulatorPanel';

export default function RightDock({ activeTab, onTabChange, summary, findings, selectedNode, onSelectNode, chat, onPreview, onAskFix, onSelectComponent, focusComponentId, onEditNode, intents, focusKb, onExportComponent, canSendImages = true, onSimNode }) {
  const [drill, setDrill] = useState(null);
  const [selectedKb, setSelectedKb] = useState(null);
  // Reset KB selection when a new export/summary loads (e.g. after apply/undo).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- clear stale KB view on new summary
    setDrill(null);
    setSelectedKb(null);
  }, [summary]);
  // Open a specific KB when a graph KB node is clicked (nonce makes repeat clicks re-fire).
  useEffect(() => {
    const id = focusKb?.id;
    if (id == null) return;
    const kb = (summary?.knowledge_bases || []).find((k) => k.knowledge_id === id);
    if (kb) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- focus from graph click
      setDrill(null);
      setSelectedKb(kb);
    }
  }, [focusKb]);   // eslint-disable-line react-hooks/exhaustive-deps -- summary intentionally excluded so apply/undo does not re-force detail
  const [width, setWidth] = useState(() => {
    const saved = Number(localStorage.getItem('tb-dock-w'));
    return saved >= 320 ? saved : 448;   // 28rem default
  });
  const errorCount = (findings || []).filter((f) => f.severity === 'error').length;
  const tabs = [
    { id: 'chat', label: 'Chat' },
    { id: 'findings', label: 'Findings', badge: errorCount || undefined },
    { id: 'properties', label: 'Properties' },
    { id: 'kb', label: 'KB' },
    { id: 'intents', label: 'Intents' },
    { id: 'tags', label: 'Tags' },
    { id: 'components', label: 'Components' },
    { id: 'simulate', label: 'Simulate' },
  ];

  // Drag the left edge to resize; clamp to [320px, 70vw] and persist.
  const startResize = (e) => {
    e.preventDefault();
    const onMove = (ev) => {
      const max = Math.round(window.innerWidth * 0.7);
      setWidth(Math.min(Math.max(window.innerWidth - ev.clientX, 320), max));
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      document.body.style.userSelect = '';
      setWidth((w) => { localStorage.setItem('tb-dock-w', String(w)); return w; });
    };
    document.body.style.userSelect = 'none';
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  return (
    <div style={{ width }} className="shrink-0 h-full border-l border-border bg-surface flex flex-col relative" data-testid="right-dock">
      <div onPointerDown={startResize} data-testid="dock-resize" title="Drag to resize"
        className="absolute left-0 top-0 h-full w-1.5 -translate-x-1/2 cursor-col-resize hover:bg-primary/40 z-20" />
      <Tabs tabs={tabs} active={activeTab} onChange={(id) => { setDrill(null); setSelectedKb(null); onTabChange(id); }} />
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' && (
          <ChatPane transcript={chat.transcript} proposal={chat.proposal} sending={chat.sending}
            onSend={chat.onSend} onRetry={chat.onRetry} onApply={chat.onApply} onReject={chat.onReject} onCancel={chat.onCancel}
            onPreview={onPreview} summary={summary} onSelectNode={onSelectNode}
            canUndo={chat.canUndo} canRedo={chat.canRedo} onUndo={chat.onUndo} onRedo={chat.onRedo}
            canSendImages={canSendImages} />
        )}
        {activeTab === 'findings' && <FindingList findings={findings} onSelect={onSelectNode} onAskFix={onAskFix} />}
        {activeTab === 'properties' && <NodePropertiesPanel node={selectedNode} summary={summary} onEditNode={onEditNode} />}
        {activeTab === 'kb' && drill && (
          <div className="flex flex-col h-full">
            <div className="flex items-center gap-2 px-4 py-2 border-b border-divider bg-surface-muted">
              <button type="button" data-testid="kb-drill-back" onClick={() => setDrill(null)} className="text-xs text-primary hover:underline">← Back</button>
              <span className="text-xs text-text-secondary">{drill.title}</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <FlowCanvas summary={drill.multi_round} onSelectNode={onSelectNode} />
            </div>
          </div>
        )}
        {activeTab === 'kb' && !drill && selectedKb && (
          <div className="flex flex-col h-full">
            <div className="flex items-center gap-2 px-4 py-2 border-b border-divider bg-surface-muted">
              <button type="button" data-testid="kb-back" onClick={() => setSelectedKb(null)} className="text-xs text-primary hover:underline">← Back</button>
              <span className="text-xs text-text-secondary">Knowledge Base</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <KBDetailPanel kb={selectedKb} onDrillIn={(kb) => setDrill(kb)} />
            </div>
          </div>
        )}
        {activeTab === 'kb' && !drill && !selectedKb && (
          <KBPlane knowledgeBases={summary?.knowledge_bases || []} onSelect={setSelectedKb} />
        )}
        {activeTab === 'intents' && <IntentsPanel intents={intents || []} />}
        {activeTab === 'tags' && <TagsPanel tags={summary?.tags || []} />}
        {activeTab === 'components' && (
          <ComponentsRail summary={summary} selectedComponentId={focusComponentId}
            onSelectComponent={onSelectComponent} onExportComponent={onExportComponent} />
        )}
        {activeTab === 'simulate' && (
          <SimulatorPanel summary={summary} onCurrentNode={onSimNode} />
        )}
      </div>
    </div>
  );
}
