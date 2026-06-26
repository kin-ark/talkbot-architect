const n = (x) => (x || 0).toLocaleString();

export default function StatisticsPage({ usage, sessions = [], activeSessionId }) {
  return (
    <div data-testid="statistics-page" className="space-y-5 text-sm text-text">
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-text-tertiary mb-2">Active session</h3>
        <div className="text-text-secondary space-y-1">
          <div>Model: <span className="text-text">{usage?.model || '—'}</span></div>
          <div>{n(usage?.input_tokens)} in · {n(usage?.output_tokens)} out · {usage?.turns || 0} turns</div>
        </div>
      </section>
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-text-tertiary mb-2">All sessions</h3>
        <table data-testid="stats-table" className="w-full text-xs">
          <thead>
            <tr className="text-text-tertiary text-left">
              <th className="py-1 pr-2 font-medium">Session</th>
              <th className="py-1 px-2 font-medium">Model</th>
              <th className="py-1 px-2 font-medium text-right">In</th>
              <th className="py-1 px-2 font-medium text-right">Out</th>
              <th className="py-1 pl-2 font-medium text-right">Turns</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((se) => {
              const u = se.usage || {};
              const active = se.id === activeSessionId;
              return (
                <tr key={se.id} className={`border-t border-divider ${active ? 'text-primary font-semibold' : 'text-text-secondary'}`}>
                  <td className="py-1 pr-2 truncate max-w-[12rem]">{se.name}</td>
                  <td className="py-1 px-2">{u.model || '—'}</td>
                  <td className="py-1 px-2 text-right">{n(u.input_tokens)}</td>
                  <td className="py-1 px-2 text-right">{n(u.output_tokens)}</td>
                  <td className="py-1 pl-2 text-right">{u.turns || 0}</td>
                </tr>
              );
            })}
            {sessions.length === 0 && (
              <tr><td colSpan={5} className="py-3 text-text-tertiary">No sessions yet.</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
