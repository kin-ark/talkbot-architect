import { useState } from 'react';
import Tabs from './ui/Tabs';
import ChatPane from './ChatPane';
import FindingList from './FindingList';
import NodePropertiesPanel from './NodePropertiesPanel';
import KBPlane from './KBPlane';
import FlowCanvas from './FlowCanvas';

export default function RightDock({ activeTab, onTabChange, summary, findings, selectedNode, onSelectNode, chat }) {
  const [drill, setDrill] = useState(null);
  const errorCount = (findings || []).filter((f) => f.severity === 'error').length;
  const tabs = [
    { id: 'chat', label: 'Chat' },
    { id: 'findings', label: 'Findings', badge: errorCount || undefined },
    { id: 'properties', label: 'Properties' },
    { id: 'kb', label: 'KB' },
  ];
  return (
    <div className="w-[28rem] max-w-[42%] shrink-0 h-full border-l border-border bg-surface flex flex-col" data-testid="right-dock">
      <Tabs tabs={tabs} active={activeTab} onChange={(id) => { setDrill(null); onTabChange(id); }} />
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' && (
          <ChatPane transcript={chat.transcript} proposal={chat.proposal} sending={chat.sending}
            onSend={chat.onSend} onApply={chat.onApply} onReject={chat.onReject} onCancel={chat.onCancel} />
        )}
        {activeTab === 'findings' && <FindingList findings={findings} onSelect={onSelectNode} />}
        {activeTab === 'properties' && <NodePropertiesPanel node={selectedNode} summary={summary} />}
        {activeTab === 'kb' && !drill && (
          <KBPlane knowledgeBases={summary?.knowledge_bases || []} onDrillIn={setDrill} />
        )}
        {activeTab === 'kb' && drill && (
          <div className="flex flex-col h-full">
            <div className="flex items-center gap-2 px-4 py-2 border-b border-divider bg-surface-muted">
              <button type="button" onClick={() => setDrill(null)} className="text-xs text-primary hover:underline">← Back</button>
              <span className="text-xs text-text-secondary">{drill.title}</span>
            </div>
            <div className="flex-1 overflow-hidden">
              <FlowCanvas summary={drill.multi_round} onSelectNode={onSelectNode} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
