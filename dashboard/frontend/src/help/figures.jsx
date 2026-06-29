/* eslint-disable react-refresh/only-export-components -- registry file; figures is an intentional non-component export */
// Theme-aware inline-SVG figures embedded in the docs via @@fig:<id>@@ sentinels.
// Colors come from Lark token utility classes + currentColor, so they adapt to light/dark.

function FigShell({ id, label, caption, children }) {
  return (
    <figure data-testid={`fig-${id}`} className="my-5 rounded-lg border border-border bg-surface-muted p-4 not-prose">
      <svg viewBox="0 0 360 180" role="img" aria-label={label} className="w-full h-auto">
        {children}
      </svg>
      <figcaption className="mt-2 text-center text-xs text-text-tertiary">{caption}</figcaption>
    </figure>
  );
}

function Box({ x, y, w, h, label, cls = 'text-text-secondary' }) {
  return (
    <g className={cls}>
      <rect x={x} y={y} width={w} height={h} rx="6" fill="none" stroke="currentColor" strokeWidth="2" />
      <text x={x + w / 2} y={y + h / 2} dominantBaseline="middle" textAnchor="middle"
        fontSize="11" fill="currentColor">{label}</text>
    </g>
  );
}

function LayoutFig() {
  return (
    <FigShell id="layout" label="App layout: top bar, session rail, graph, right dock"
      caption="The four areas of the workspace">
      <g className="text-primary"><Box x={10} y={12} w={340} h={26} label="Top bar — bot name · undo/redo · export" cls="text-primary" /></g>
      <Box x={10} y={46} w={70} h={120} label="Session rail" />
      <Box x={88} y={46} w={170} h={120} label="Flow graph" cls="text-text" />
      <Box x={266} y={46} w={84} h={120} label="Right dock" />
    </FigShell>
  );
}

function NodeTypesFig() {
  const rows = [
    ['talk', 'speaks + branches'],
    ['exit', 'ends the call'],
    ['transfer', 'hands to a human'],
    ['goto', 'jump to a component'],
    ['goto_kb', 'jump to a Knowledge Base'],
    ['conditional', 'routes on a variable'],
    ['assign', 'sets a variable'],
    ['nested', 'delegates to a child canvas'],
    ['exit_port', 'named return from a child'],
  ];
  return (
    <FigShell id="node-types" label="The nine node types" caption="The nine supported node types">
      {rows.map((r, i) => {
        const col = i < 5 ? 0 : 1;
        const row = i < 5 ? i : i - 5;
        const x = 12 + col * 180;
        const y = 16 + row * 32;
        return (
          <g key={r[0]} className="text-text">
            <circle cx={x + 6} cy={y} r="5" className="text-primary" fill="currentColor" />
            <text x={x + 18} y={y} dominantBaseline="middle" fontSize="11" fill="currentColor" fontWeight="600">{r[0]}</text>
            <text x={x + 18} y={y + 13} dominantBaseline="middle" fontSize="9"
              className="text-text-tertiary" fill="currentColor">{r[1]}</text>
          </g>
        );
      })}
    </FigShell>
  );
}

function Arrow({ x1, x2, y }) {
  return (
    <g className="text-text-tertiary">
      <line x1={x1} y1={y} x2={x2 - 6} y2={y} stroke="currentColor" strokeWidth="2" />
      <path d={`M ${x2 - 6} ${y - 4} L ${x2} ${y} L ${x2 - 6} ${y + 4} Z`} fill="currentColor" />
    </g>
  );
}

function ProposalFlowFig() {
  const steps = ['Ask in chat', 'Proposal + diff', 'Apply', 'Undo / Redo'];
  return (
    <FigShell id="proposal-flow" label="Edit lifecycle: ask, proposal, apply, undo"
      caption="Every edit is a reviewable proposal — nothing changes until you Apply">
      {steps.map((s, i) => {
        const x = 8 + i * 88;
        return <Box key={s} x={x} y={70} w={72} h={40} label={s} cls={i === 2 ? 'text-primary' : 'text-text-secondary'} />;
      })}
      {[0, 1, 2].map((i) => <Arrow key={i} x1={8 + i * 88 + 72} x2={8 + (i + 1) * 88} y={90} />)}
    </FigShell>
  );
}

function SeverityFig() {
  return (
    <FigShell id="severity" label="Finding severities: error vs warning"
      caption="Errors break import; warnings break deploy. Export warns if errors remain.">
      <g className="text-error">
        <circle cx="24" cy="40" r="7" fill="currentColor" />
        <text x="40" y="40" dominantBaseline="middle" fontSize="12" fill="currentColor" fontWeight="600">Error</text>
      </g>
      <text x="100" y="40" dominantBaseline="middle" fontSize="11" className="text-text-secondary" fill="currentColor">breaks import — must fix</text>
      <g className="text-warning">
        <circle cx="24" cy="80" r="7" fill="currentColor" />
        <text x="40" y="80" dominantBaseline="middle" fontSize="12" fill="currentColor" fontWeight="600">Warning</text>
      </g>
      <text x="100" y="80" dominantBaseline="middle" fontSize="11" className="text-text-secondary" fill="currentColor">incomplete — may break deploy</text>
      <g className="text-text-tertiary">
        <text x="24" y="130" fontSize="10" fill="currentColor">Export asks for confirmation when error-level findings remain.</text>
      </g>
    </FigShell>
  );
}

function KbFlowFig() {
  return (
    <FigShell id="kb-flow" label="Knowledge Base flow and the multi-round variant"
      caption="A KB answers a triggering intent; a multi-round KB delegates to a component">
      <Box x={10} y={70} w={86} h={40} label="Intent" />
      <Arrow x1={96} x2={132} y={90} />
      <Box x={132} y={70} w={86} h={40} label="Knowledge Base" cls="text-primary" />
      <Arrow x1={218} x2={254} y={90} />
      <Box x={254} y={70} w={96} h={40} label="Answer" />
      <Arrow x1={175} x2={175} y={110} />
      <g className="text-text-tertiary">
        <line x1="175" y1="110" x2="175" y2="140" stroke="currentColor" strokeWidth="2" strokeDasharray="3 3" />
      </g>
      <Box x={132} y={140} w={140} h={32} label="Multi-round → component" cls="text-text-tertiary" />
    </FigShell>
  );
}

export const figures = {
  layout: LayoutFig,
  'node-types': NodeTypesFig,
  'proposal-flow': ProposalFlowFig,
  severity: SeverityFig,
  'kb-flow': KbFlowFig,
};
