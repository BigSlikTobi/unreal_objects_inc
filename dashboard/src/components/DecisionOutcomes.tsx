import type { DisposalOrderDTO } from '../types';

interface Props {
  orders: DisposalOrderDTO[];
}

const OUTCOME_CONFIG: Record<
  string,
  { label: string; barClass: string; badgeClass: string; progressColor: string }
> = {
  APPROVED: {
    label: 'Approved',
    barClass: 'status-approved',
    badgeClass: 'status-badge-green',
    progressColor: 'var(--green)',
  },
  REJECTED: {
    label: 'Rejected',
    barClass: 'status-rejected',
    badgeClass: 'status-badge-red',
    progressColor: 'var(--red)',
  },
  APPROVAL_REQUIRED: {
    label: 'Need Approval',
    barClass: 'status-pending',
    badgeClass: 'status-badge-amber',
    progressColor: 'var(--amber)',
  },
};

export function DecisionOutcomes({ orders }: Props) {
  const counts: Record<string, number> = {
    APPROVED: 0,
    REJECTED: 0,
    APPROVAL_REQUIRED: 0,
  };

  for (const order of orders) {
    const outcome = order.decision_outcome;
    if (outcome && outcome in counts) counts[outcome]++;
  }

  const total = Math.max(
    Object.values(counts).reduce((sum, v) => sum + v, 0),
    1,
  );

  return (
    <section
      className="console-card console-side-panel p-5"
      aria-label="Guardrail decision outcomes"
    >
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Guardrail Outcomes</p>
          <h2 className="editorial-title console-side-title">Action Outcomes</h2>
          <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            How Unreal Objects is shaping autonomous waste decisions.
          </p>
        </div>
        <span
          className="status-badge status-badge-green"
          aria-label="Data is live"
        >
          <span className="status-badge-dot" aria-hidden="true" />
          Live
        </span>
      </div>

      <div className="console-inset console-outcome-panel" style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {Object.entries(OUTCOME_CONFIG).map(([key, cfg]) => {
            const count = counts[key] || 0;
            const pct = ((count / total) * 100).toFixed(1);
            return (
              <div key={key}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '0.5rem',
                  }}
                >
                  <span
                    className={`status-badge ${cfg.badgeClass}`}
                    aria-label={`${cfg.label}: ${count}`}
                  >
                    <span className="status-badge-dot" aria-hidden="true" />
                    {cfg.label}
                  </span>
                  <span
                    style={{
                      fontFamily: '"Space Grotesk", sans-serif',
                      fontSize: '0.875rem',
                      fontWeight: 700,
                      color: 'var(--text-primary)',
                    }}
                  >
                    {count}
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 400,
                        color: 'var(--text-muted)',
                        marginLeft: '0.3rem',
                      }}
                    >
                      ({pct}%)
                    </span>
                  </span>
                </div>
                <div className="progress-track" role="progressbar" aria-valuenow={count} aria-valuemax={total} aria-label={`${cfg.label} progress`}>
                  <div
                    className="progress-bar"
                    style={{
                      width: `${(count / total) * 100}%`,
                      backgroundColor: cfg.progressColor,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
