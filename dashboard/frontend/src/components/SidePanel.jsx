import { useState } from 'react';
import FlowCanvas from './FlowCanvas';
import FindingList from './FindingList';
import NodePropertiesPanel from './NodePropertiesPanel';
import KBPlane from './KBPlane';

const TABS = ['Graph', 'Findings', 'Properties', 'Knowledge Bases'];

export default function SidePanel({ summary, findings, selectedNode, onSelectNode }) {
  const [tab, setTab] = useState('Graph');
  const [drill, setDrill] = useState(null);
  return (
    <div className="w-[44rem] max-w-[50%] h-full border-l border-slate-200 bg-white flex flex-col" data-testid="side-panel">
      <div className="flex border-b border-slate-200">
        {TABS.map((t) => (
          <button key={t} onClick={() => { setTab(t); setDrill(null); }}
            className={`px-4 py-2 text-sm ${tab === t ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-500'}`}>{t}</button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {tab === 'Graph' && <FlowCanvas summary={summary} onSelectNode={onSelectNode} />}
        {tab === 'Findings' && <FindingList findings={findings} onSelect={onSelectNode} />}
        {tab === 'Properties' && <NodePropertiesPanel node={selectedNode} summary={summary} />}
        {tab === 'Knowledge Bases' && !drill && (
          <KBPlane knowledgeBases={summary?.knowledge_bases || []} onDrillIn={setDrill} />
        )}
        {tab === 'Knowledge Bases' && drill && (
          <div className="flex flex-col h-full">
            <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-200 bg-slate-50">
              <button onClick={() => setDrill(null)}
                className="text-xs text-indigo-600 hover:underline">← Back</button>
              <span className="text-xs text-slate-500">{drill.title}</span>
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
