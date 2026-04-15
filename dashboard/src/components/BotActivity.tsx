import { useMemo, useState } from 'react';
import { Bot } from 'lucide-react';
import type { ApprovalItemDTO, CompanyStatus, DisposalOrderDTO } from '../types';

interface Props {
  orders: DisposalOrderDTO[];
  approvals: ApprovalItemDTO[];
  status: CompanyStatus | null;
}

function elapsed(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '<1m';
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function money(value: number | null): string {
  return value == null ? '—' : `€${value.toFixed(0)}`;
}

export function BotActivity({ orders, approvals, status }: Props) {
  const [botFilter, setBotFilter] = useState<string>('all');

  const botConnected = status?.bot_connected ?? false;
  const engineName = status?.bot_identity ?? 'Bot';

  // Collect unique bot identities from assigned_to
  const botIdentities = useMemo(() => {
    const set = new Set<string>();
    for (const o of orders) {
      if (o.assigned_to) set.add(o.assigned_to);
    }
    return [...set].sort();
  }, [orders]);

  // Build a set of order IDs belonging to the selected bot (for linking approvals)
  const botOrderIds = useMemo(() => {
    if (botFilter === 'all') return null;
    const ids = new Set<string>();
    for (const o of orders) {
      if (o.assigned_to === botFilter) ids.add(o.order_id);
    }
    return ids;
  }, [orders, botFilter]);

  // Filter orders by bot
  const filteredOrders = useMemo(() => {
    if (botFilter === 'all') return orders;
    return orders.filter((o) => o.assigned_to === botFilter);
  }, [orders, botFilter]);

  // Filter approvals by matching order_id to the selected bot's orders
  const filteredApprovals = useMemo(() => {
    if (!botOrderIds) return approvals;
    return approvals.filter((a) => botOrderIds.has(a.order_id));
  }, [approvals, botOrderIds]);

  const claimed = filteredOrders.filter((o) => o.status === 'claimed');
  const blocked = filteredOrders.filter((o) => o.status === 'blocked').length;
  const completed = filteredOrders.filter((o) => o.status === 'completed').length;
  const rejected = filteredOrders.filter((o) => o.status === 'rejected').length;

  // Decision outcome counts
  const outcomeCounts = { APPROVED: 0, REJECTED: 0, APPROVAL_REQUIRED: 0 };
  for (const o of filteredOrders) {
    const oc = o.decision_outcome;
    if (oc && oc in outcomeCounts) outcomeCounts[oc as keyof typeof outcomeCounts]++;
  }
  const outcomeTotal = Math.max(outcomeCounts.APPROVED + outcomeCounts.REJECTED + outcomeCounts.APPROVAL_REQUIRED, 1);

  const recentCompleted = filteredOrders
    .filter((o) => o.status === 'completed')
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 8);
  const recentRejected = filteredOrders
    .filter((o) => o.status === 'rejected')
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 8);
  const recentPending = [...filteredApprovals]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 8);

  return (
    <section className="view-page flex min-h-0 flex-col" aria-label="Bot activity">
      {/* Header */}
      <div className="bot-page-header">
        <div>
          <p className="console-panel-kicker">Autonomous Agent</p>
          <h2 className="console-panel-title">{engineName}</h2>
        </div>
        <div className="console-panel-actions">
          <span
            className={`status-badge ${botConnected ? 'status-badge-green' : 'status-badge-red'}`}
          >
            <span className="status-badge-dot" aria-hidden="true" />
            {botConnected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Bot filter bar */}
      {botIdentities.length > 0 && (
        <div className="order-filter-bar">
          <button
            type="button"
            className={`order-filter-chip ${botFilter === 'all' ? 'order-filter-chip-active' : ''}`}
            onClick={() => setBotFilter('all')}
          >
            All Bots
            <span className="order-filter-count">{orders.filter((o) => o.assigned_to).length}</span>
          </button>
          {botIdentities.map((id) => {
            const count = orders.filter((o) => o.assigned_to === id).length;
            return (
              <button
                key={id}
                type="button"
                className={`order-filter-chip ${botFilter === id ? 'order-filter-chip-active' : ''}`}
                onClick={() => setBotFilter(id)}
              >
                {id}
                <span className="order-filter-count">{count}</span>
              </button>
            );
          })}
        </div>
      )}

      <div className="view-data-card bot-page-body">
        {/* ── KPI strip ── */}
        <div className="bot-kpi-strip">
          {[
            { label: 'Claimed', value: claimed.length, color: 'var(--blue)' },
            { label: 'Completed', value: completed, color: 'var(--green)' },
            { label: 'Blocked', value: blocked, color: 'var(--amber)' },
            { label: 'Rejected', value: rejected, color: 'var(--red)' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bot-kpi-item">
              <span className="bot-kpi-value" style={{ color }}>{value}</span>
              <span className="bot-kpi-label">{label}</span>
            </div>
          ))}
        </div>

        {/* ── Two-column: Outcomes + Live Claims ── */}
        <div className="bot-mid-grid">
          {/* Guardrail outcomes */}
          <div className="bot-section">
            <div className="bot-section-head">
              <span className="bot-section-title">Guardrail Outcomes</span>
            </div>
            <div className="bot-outcomes">
              {([
                { key: 'APPROVED', label: 'Approved', color: 'var(--green)', badge: 'status-badge-green' },
                { key: 'REJECTED', label: 'Rejected', color: 'var(--red)', badge: 'status-badge-red' },
                { key: 'APPROVAL_REQUIRED', label: 'Need Approval', color: 'var(--amber)', badge: 'status-badge-amber' },
              ] as const).map(({ key, label, color, badge }) => {
                const count = outcomeCounts[key];
                const pct = ((count / outcomeTotal) * 100).toFixed(0);
                return (
                  <div key={key} className="bot-outcome-row">
                    <div className="bot-outcome-head">
                      <span className={`status-badge ${badge}`}>
                        <span className="status-badge-dot" aria-hidden="true" />
                        {label}
                      </span>
                      <span className="bot-outcome-count">
                        {count} <span className="bot-outcome-pct">{pct}%</span>
                      </span>
                    </div>
                    <div className="progress-track" role="progressbar" aria-valuenow={count} aria-valuemax={outcomeTotal}>
                      <div
                        className="progress-bar"
                        style={{ width: `${(count / outcomeTotal) * 100}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Live claims */}
          <div className="bot-section">
            <div className="bot-section-head">
              <span className="bot-section-title">Live Claims</span>
              <span className="pricing-section-count">{claimed.length}</span>
            </div>
            {!botConnected ? (
              <div className="bot-empty-state">
                <Bot className="h-6 w-6" style={{ opacity: 0.3 }} aria-hidden="true" />
                <p>No bot connected.</p>
              </div>
            ) : claimed.length === 0 ? (
              <div className="bot-empty-state">
                <p>No active claims right now.</p>
              </div>
            ) : (
              <div className="bot-claim-list">
                {claimed.map((o) => (
                  <div key={o.order_id} className="bot-claim-row">
                    <div className="bot-claim-info">
                      <span className="pulse-dot pulse-dot-compact" aria-hidden="true" />
                      <span className="bot-claim-waste">{o.declared_waste_type}</span>
                      <span className="bot-claim-vol">{o.quantity_m3.toFixed(1)} m³</span>
                      <span className="bot-claim-price">{money(o.offered_price_eur)}</span>
                    </div>
                    <span className="bot-claim-time">{elapsed(o.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Recent Activity: 3 columns ── */}
        <div className="bot-history-grid">
          <div className="bot-section">
            <div className="bot-section-head">
              <span className="bot-section-title">Completed</span>
              <span className="pricing-section-count">{recentCompleted.length}</span>
            </div>
            {recentCompleted.length === 0 ? (
              <div className="bot-empty-state"><p>None yet.</p></div>
            ) : (
              <div className="bot-history-list">
                {recentCompleted.map((o) => (
                  <HistoryRow key={o.order_id} order={o} />
                ))}
              </div>
            )}
          </div>

          <div className="bot-section">
            <div className="bot-section-head">
              <span className="bot-section-title">Rejected</span>
              <span className="pricing-section-count">{recentRejected.length}</span>
            </div>
            {recentRejected.length === 0 ? (
              <div className="bot-empty-state"><p>None yet.</p></div>
            ) : (
              <div className="bot-history-list">
                {recentRejected.map((o) => (
                  <HistoryRow key={o.order_id} order={o} />
                ))}
              </div>
            )}
          </div>

          <div className="bot-section">
            <div className="bot-section-head">
              <span className="bot-section-title">Pending Approvals</span>
              <span className="pricing-section-count">{recentPending.length}</span>
            </div>
            {recentPending.length === 0 ? (
              <div className="bot-empty-state"><p>None right now.</p></div>
            ) : (
              <div className="bot-history-list">
                {recentPending.map((a) => (
                  <div key={a.request_id} className="bot-history-item">
                    <div className="bot-history-item-head">
                      <span className="bot-history-item-title">{a.title}</span>
                      <span className="bot-history-item-time">{elapsed(a.created_at)}</span>
                    </div>
                    <div className="bot-history-item-tags">
                      <span className="ghost-pill">{a.bot_action.replace(/_/g, ' ')}</span>
                      <span className="ghost-pill">{a.matched_rules.length} rule{a.matched_rules.length === 1 ? '' : 's'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function HistoryRow({ order }: { order: DisposalOrderDTO }) {
  return (
    <div className="bot-history-item">
      <div className="bot-history-item-head">
        <span className="bot-history-item-title">{order.title}</span>
        <span className="bot-history-item-time">{elapsed(order.created_at)}</span>
      </div>
      <div className="bot-history-item-tags">
        <span className="ghost-pill">{order.declared_waste_type}</span>
        <span className="ghost-pill">{order.quantity_m3.toFixed(1)} m³</span>
        {order.bot_action && (
          <span className="ghost-pill">{order.bot_action.replace(/_/g, ' ')}</span>
        )}
      </div>
    </div>
  );
}
