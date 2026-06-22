import React from 'react';
export default function FindingList({ findings = [] }) {
  return (
    <ul data-testid="finding-list">
      {findings.map((f, i) => (
        <li key={i}><span>{f.code}</span> {f.message}</li>
      ))}
    </ul>
  );
}
