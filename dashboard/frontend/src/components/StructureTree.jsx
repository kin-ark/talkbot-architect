import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Folder, File, Component } from 'lucide-react';

const TreeNode = ({ node, level = 0 }) => {
    const [isOpen, setIsOpen] = useState(level < 2);
    const hasChildren = node.children && node.children.length > 0;

    return (
        <div className="ml-4">
            <div 
                className={`flex items-center py-1 gap-2 cursor-pointer hover:bg-slate-50 rounded px-2 ${!hasChildren ? 'text-gray-600' : 'text-gray-800 font-medium'}`}
                onClick={() => hasChildren && setIsOpen(!isOpen)}
            >
                {hasChildren ? (
                    isOpen ? <ChevronDown size={16} className="text-gray-400"/> : <ChevronRight size={16} className="text-gray-400"/>
                ) : (
                    <span className="w-4"></span>
                )}
                {level === 0 ? <Folder size={16} className="text-indigo-500" /> : 
                 level === 1 ? <Component size={16} className="text-blue-500" /> : 
                 <File size={14} className="text-gray-400" />}
                <span className="text-sm truncate select-none">{node.name}</span>
            </div>
            {isOpen && hasChildren && (
                <div className="border-l border-gray-200 ml-3">
                    {node.children.map((child, idx) => (
                        <TreeNode key={child.uuid || idx} node={child} level={level + 1} />
                    ))}
                </div>
            )}
        </div>
    );
};

export default function StructureTree({ summary }) {
    if (!summary || Object.keys(summary).length === 0) {
        return <div className="text-sm text-gray-500">No summary available</div>;
    }

    return (
        <div className="structure-tree">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Dialogue Structure</h3>
            <div className="bg-white rounded border border-gray-100 p-2 overflow-x-auto">
                <TreeNode node={summary} />
            </div>
        </div>
    );
}
