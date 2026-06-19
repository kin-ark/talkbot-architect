import React from 'react';

export default function StructureTree({ summary }) {
    if (!summary) return <div>No summary available</div>;
    return <div className="structure-tree">Summary Loaded</div>;
}
