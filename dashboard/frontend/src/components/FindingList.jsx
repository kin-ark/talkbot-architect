import React from 'react';

const SEVERITY_MAP = {
  error: {
    border: 'border-red-100',
    badge: 'bg-red-600',
    label: 'bg-red-100 text-red-700 border-red-200'
  },
  warning: {
    border: 'border-amber-100',
    badge: 'bg-amber-500',
    label: 'bg-amber-100 text-amber-700 border-amber-200'
  }
};

export default function FindingList({ findings = [] }) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-800">Audit Log</h2>
        <div className="flex gap-2 text-xs">
          <span className={`px-2 py-1 rounded-full border ${SEVERITY_MAP.error.label}`}>Errors</span>
          <span className={`px-2 py-1 rounded-full border ${SEVERITY_MAP.warning.label}`}>Warnings</span>
        </div>
      </div>
      
      <div className="grid gap-3">
        {findings.map((f) => {
          const style = SEVERITY_MAP[f.severity] || SEVERITY_MAP.warning;
          const key = `${f.code}-${f.location.entity}-${f.location.id}-${f.location.field}`;
          
          return (
            <div key={key} className={`p-4 rounded-lg border shadow-sm transition-all hover:shadow-md bg-white ${style.border}`}>
              <div className="flex justify-between items-start gap-4 mb-2">
                <div className="flex flex-col gap-1">
                  <span className={`w-fit font-mono text-[10px] font-bold px-1.5 py-0.5 rounded text-white ${style.badge}`}>
                    {f.code}
                  </span>
                  <span className="text-[10px] uppercase text-gray-400 font-semibold tracking-wider">
                    {f.severity}
                  </span>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-mono text-gray-500">{f.location.entity}:{f.location.id?.slice(0,8)}</p>
                  <p className="text-[10px] text-gray-400 font-medium lowercase">.{f.location.field}</p>
                </div>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed font-medium">{f.message}</p>
            </div>
          );
        })}
        {findings.length === 0 && (
          <div className="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-200">
            <p className="text-gray-500 font-medium">No findings detected. Your dialogue export is clean!</p>
          </div>
        )}
      </div>
    </div>
  );
}
