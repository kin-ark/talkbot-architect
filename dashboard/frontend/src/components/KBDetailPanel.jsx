import { PhoneOff, Clock } from 'lucide-react';

function Field({ label, children }) {
  return (
    <div className="mb-4">
      <div className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider mb-1">{label}</div>
      <div className="text-sm text-text">{children}</div>
    </div>
  );
}

const Chip = ({ children }) => (
  <span className="inline-block text-[11px] bg-surface-muted text-text border border-border rounded px-1.5 py-0.5 mr-1 mb-1">{children}</span>
);

export default function KBDetailPanel({ kb, onDrillIn }) {
  if (!kb) return <div className="p-6 text-text-tertiary text-sm" data-testid="kb-detail-panel">Select a KB.</div>;

  // Intent chips: render intent_names directly (includes fallback id-strings).
  const intentChips = kb.intent_names || [];
  const triggerLabel = kb.trigger_type === 'system' ? 'System Trigger' : 'Intent Trigger';
  const originLabel = kb.is_user_created ? 'user-created' : 'system';

  return (
    <div className="p-6 overflow-y-auto h-full" data-testid="kb-detail-panel">
      <div className="mb-4">
        <div className="text-base font-semibold text-text">{kb.title}</div>
        <div className="text-[11px] text-text-tertiary">id {kb.knowledge_id}</div>
      </div>

      <Field label="Trigger">
        <span className="text-[11px] bg-surface-muted text-primary rounded px-1.5 py-0.5 mr-2">{triggerLabel}</span>
        <span className="text-[11px] text-text-tertiary">{originLabel}</span>
      </Field>

      <Field label="Trigger Intents">
        {intentChips.length === 0
          ? <span className="text-text-tertiary">No intents</span>
          : <div>{intentChips.map((n, i) => <Chip key={`${n}-${i}`}>{n}</Chip>)}</div>}
      </Field>

      <Field label="Answers">
        {(kb.answers || []).length === 0
          ? <span className="text-text-tertiary">No answers</span>
          : (
            <ul className="space-y-1">
              {kb.answers.map((a, i) => (
                <li key={i} className="text-xs bg-surface-muted border border-border rounded px-2 py-1">
                  <div className="text-text">{a.text}</div>
                  <div className="text-[10px] text-text-tertiary mt-0.5 inline-flex items-center gap-1">
                    {a.after === 'hangup'
                      ? <><PhoneOff size={11} /> Hang up</>
                      : <><Clock size={11} /> Wait for response</>}
                  </div>
                </li>
              ))}
            </ul>
          )}
      </Field>

      {kb.multi_round_target && (
        <Field label="Multi-Round">
          <div className="flex items-center gap-2">
            <span className="text-text">{kb.multi_round_target}</span>
            <button type="button" data-testid="kb-drill" onClick={() => onDrillIn?.(kb)}
              className="text-xs rounded-md px-2 py-1 bg-primary text-primary-fg hover:bg-primary-hover">
              Drill into flow ▸
            </button>
          </div>
        </Field>
      )}
    </div>
  );
}
