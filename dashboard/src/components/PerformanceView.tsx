import type { ContainerDTO, DisposalOrderDTO, EconomicsSnapshot } from '../types';

interface Props {
  orders: DisposalOrderDTO[];
  economics: EconomicsSnapshot | null;
  containers: ContainerDTO[];
}

function money(value: number | null | undefined): string {
  if (value == null) return '—';
  const rounded = Math.round(value);
  return `${rounded < 0 ? '-' : ''}€${Math.abs(rounded)}`;
}

export function PerformanceView({ orders, economics, containers }: Props) {
  const completed = orders.filter((order) => order.status === 'completed').length;
  const rejected = orders.filter((order) => order.status === 'rejected').length;
  const blocked = orders.filter((order) => order.status === 'blocked').length;
  const guarded = orders.filter((order) => order.decision_outcome === 'APPROVAL_REQUIRED').length;
  const hotContainers = [...containers].sort((a, b) => b.fill_ratio - a.fill_ratio).slice(0, 3);
  const totalInvoicedRevenue = economics?.invoiced_revenue_eur ?? 0;
  const avgOrderValue = completed > 0 ? totalInvoicedRevenue / completed : 0;

  return (
    <div className="console-view-stack">
      <div className="console-dual-grid">
        <section className="console-card p-5">
          <div className="console-panel-header">
            <div>
              <p className="console-panel-kicker">Performance</p>
              <h2 className="console-side-title editorial-title text-[var(--text-primary)]">Outcome Mix</h2>
            </div>
            <span className="ghost-pill">{orders.length} tracked</span>
          </div>
          <div className="console-inset mt-4 grid gap-3 p-4 sm:grid-cols-3">
            <div className="overview-stat">
              <span className="section-label">Completed</span>
              <span className="overview-stat-value">{completed}</span>
            </div>
            <div className="overview-stat">
              <span className="section-label">Rejected</span>
              <span className="overview-stat-value">{rejected}</span>
            </div>
            <div className="overview-stat">
              <span className="section-label">Approval Gated</span>
              <span className="overview-stat-value">{blocked || guarded}</span>
            </div>
          </div>
        </section>

        <section className="console-card p-5">
          <div className="console-panel-header">
            <div>
              <p className="console-panel-kicker">Economics</p>
              <h2 className="console-side-title editorial-title text-[var(--text-primary)]">Commercial Quality</h2>
            </div>
            <span className="ghost-pill">Live</span>
          </div>
          <div className="console-inset mt-4 grid gap-3 p-4 sm:grid-cols-2">
            <div className="overview-stat">
              <span className="section-label">Net Profit</span>
              <span className="overview-stat-value">{money(economics?.profit_eur)}</span>
            </div>
            <div className="overview-stat">
              <span className="section-label">Cash Balance</span>
              <span className="overview-stat-value">{money(economics?.cash_balance_eur)}</span>
            </div>
            <div className="overview-stat">
              <span className="section-label">Avg Invoiced Order</span>
              <span className="overview-stat-value">{money(avgOrderValue)}</span>
            </div>
            <div className="overview-stat">
              <span className="section-label">Receivables</span>
              <span className="overview-stat-value">{money(economics?.accounts_receivable_eur)}</span>
            </div>
            <div className="overview-stat">
              <span className="section-label">Daily Burn</span>
              <span className="overview-stat-value">{money(economics?.daily_burn_eur)}</span>
            </div>
          </div>
        </section>
      </div>

      <section className="console-card p-5">
        <div className="console-panel-header">
          <div>
            <p className="console-panel-kicker">Pressure Points</p>
            <h2 className="console-side-title editorial-title text-[var(--text-primary)]">Highest Fill Containers</h2>
          </div>
          <span className="ghost-pill">{hotContainers.length} critical</span>
        </div>
        <div className="console-side-list mt-4 space-y-3">
          {hotContainers.map((container) => (
            <div key={container.container_id} className="console-inset px-4 py-4">
              <div className="mb-2 flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-[var(--text-primary)]">{container.label}</div>
                  <div className="text-xs text-[var(--text-secondary)]">{container.waste_type}</div>
                </div>
                <div className="text-right text-sm text-[var(--text-primary)]">
                  {(container.fill_ratio * 100).toFixed(0)}%
                </div>
              </div>
              <div className="progress-track">
                <div
                  className="progress-bar"
                  style={{
                    width: `${Math.min(container.fill_ratio * 100, 100)}%`,
                    backgroundColor: 'var(--blue)',
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
