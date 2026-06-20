import React from 'react';

export default function NodePropertiesPanel({ selectedNode, knowledgeBases = [] }) {
  if (!selectedNode) return null;

  const getKBTitle = (kbId) => {
    const kb = knowledgeBases.find((k) => k.id === kbId);
    return kb ? kb.title : kbId;
  };

  const { name, node_type, allowedKBs = [] } = selectedNode;

  return (
    <div 
      className="w-80 h-full bg-white border-l border-slate-200 p-6 overflow-y-auto shadow-sm flex flex-col shrink-0" 
      data-testid="node-properties-panel"
    >
      <h2 className="text-lg font-semibold text-slate-800 mb-6 border-b border-slate-100 pb-2">
        Properties
      </h2>
      
      <div className="mb-5">
        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
          Label
        </label>
        <div className="text-sm font-medium text-slate-700" data-testid="prop-label">
          {name || 'N/A'}
        </div>
      </div>
      
      <div className="mb-5">
        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
          Type
        </label>
        <div className="text-sm font-medium text-slate-700" data-testid="prop-type">
          {node_type || 'N/A'}
        </div>
      </div>

      <div className="mb-5">
        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
          Allowed KBs
        </label>
        {allowedKBs && allowedKBs.length > 0 ? (
          <ul className="space-y-2" data-testid="prop-kbs">
            {allowedKBs.map((kbId, idx) => (
              <li 
                key={idx} 
                className="text-xs font-medium text-slate-600 bg-slate-50 px-2 py-1.5 rounded border border-slate-200"
              >
                {getKBTitle(kbId)}
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-sm text-slate-400 italic" data-testid="prop-no-kbs">None</div>
        )}
      </div>
    </div>
  );
}
