import type { CompanyStatus } from '../types';

interface Props {
  status: CompanyStatus | null;
  rulesCount: number;
  marketQuoteCount: number;
  operationalOptionCount: number;
}

export function OverviewStatsPanel({ status, rulesCount, marketQuoteCount, operationalOptionCount }: Props) {
  const stats = status?.stats;

  return (
    <section className="console-card console-side-panel p-5" aria-label="Operations snapshot">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Operations Snapshot</p>
          <h2 className="editorial-title console-side-title text-[var(--text-primary)]">Showcase Metrics</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Company posture, pricing depth, and current operational surface.
          </p>
        </div>
        <span className="ghost-pill">Run #{status?.current_run_id ?? 1}</span>
      </div>

      <div className="console-inset mt-4 grid gap-3 p-4 sm:grid-cols-2">
        <div className="overview-stat">
          <span className="section-label">Active Containers</span>
          <span className="overview-stat-value">{stats?.active_containers ?? 0}</span>
        </div>
        <div className="overview-stat">
          <span className="section-label">Extra Rentals</span>
          <span className="overview-stat-value">{stats?.rented_extra_containers ?? 0}</span>
        </div>
        <div className="overview-stat">
          <span className="section-label">Open Orders</span>
          <span className="overview-stat-value">{stats?.open_orders ?? 0}</span>
        </div>
        <div className="overview-stat">
          <span className="section-label">Blocked Actions</span>
          <span className="overview-stat-value">{stats?.blocked_orders ?? 0}</span>
        </div>
        <div className="overview-stat">
          <span className="section-label">Active Rules</span>
          <span className="overview-stat-value">{rulesCount}</span>
        </div>
        <div className="overview-stat">
          <span className="section-label">Pricing References</span>
          <span className="overview-stat-value">{marketQuoteCount + operationalOptionCount}</span>
        </div>
      </div>
    </section>
  );
}
