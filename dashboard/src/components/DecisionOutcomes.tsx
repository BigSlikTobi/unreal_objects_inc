import type { DisposalOrderDTO } from '../types';

interface Props {
  orders: DisposalOrderDTO[];
}

const OUTCOME_CONFIG: Record<string, { label: string; color: string; bar: string }> = {
  APPROVED: { label: 'Approved', color: 'text-emerald-400', bar: 'bg-emerald-500' },
  REJECTED: { label: 'Rejected', color: 'text-red-400', bar: 'bg-red-500' },
  APPROVAL_REQUIRED: { label: 'Need Approval', color: 'text-amber-400', bar: 'bg-amber-500' },
};

export function DecisionOutcomes({ orders }: Props) {
  const counts: Record<string, number> = { APPROVED: 0, REJECTED: 0, APPROVAL_REQUIRED: 0 };
  for (const order of orders) {
    const outcome = order.decision_outcome;
    if (outcome && outcome in counts) counts[outcome]++;
  }
  const total = Math.max(Object.values(counts).reduce((sum, value) => sum + value, 0), 1);

  return (
    <section className="console-card console-side-panel p-5" aria-label="Guardrail outcomes">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Guardrail Outcomes</p>
          <h2 className="editorial-title console-side-title text-[var(--text-primary)]">Action Outcomes</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            How Unreal Objects is shaping autonomous waste decisions.
          </p>
        </div>
        <span className="ghost-pill">Live</span>
      </div>
      <div className="console-inset console-outcome-panel space-y-4 p-4">
        {Object.entries(OUTCOME_CONFIG).map(([key, cfg]) => {
          const count = counts[key] || 0;
          const pct = ((count / total) * 100).toFixed(1);
          return (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between">
                <span className={`text-sm font-medium ${cfg.color}`}>{cfg.label}</span>
                <span className="font-mono text-sm text-[var(--text-primary)]">
                  {count} <span className="text-[var(--text-secondary)]">({pct}%)</span>
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[rgba(2,8,19,0.95)]">
                <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${(count / total) * 100}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
