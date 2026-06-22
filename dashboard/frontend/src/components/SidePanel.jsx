import React, { useState } from 'react';
import FlowCanvas from './FlowCanvas';
import FindingList from './FindingList';
import NodePropertiesPanel from './NodePropertiesPanel';

const TABS = ['Graph', 'Findings', 'Properties'];

export default function SidePanel({ summary, findings, selectedNode, onSelectNode }) {
  const [tab, setTab] = useState('Graph');
  return (
    <div className="w-[44rem] max-w-[50%] h-full border-l border-slate-200 bg-white flex flex-col" data-testid="side-panel">
      <div className="flex border-b border-slate-200">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm ${tab === t ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-slate-500'}`}>{t}</button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {tab === 'Graph' && <FlowCanvas summary={summary} onSelectNode={onSelectNode} />}
        {tab === 'Findings' && <FindingList findings={findings} onSelect={onSelectNode} />}
        {tab === 'Properties' && <NodePropertiesPanel node={selectedNode} summary={summary} />}
      </div>
    </div>
  );
}
