import { useState } from 'react';
import { Bot, ChevronDown } from 'lucide-react';
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

export function BotActivity({ orders, approvals, status }: Props) {
  const [activityExpanded, setActivityExpanded] = useState(false);
  const claimed = orders.filter((order) => order.status === 'claimed');
  const recentApproved = orders
    .filter((order) => order.status === 'completed')
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    .slice(0, 5);
  const recentRejected = orders
    .filter((order) => order.status === 'rejected')
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    .slice(0, 5);
  const recentPending = [...approvals]
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    .slice(0, 5);
  const blocked = orders.filter((order) => order.status === 'blocked').length;
  const completed = orders.filter((order) => order.status === 'completed').length;
  const botConnected = status?.bot_connected ?? false;
  const engineName = (status?.bot_identity ?? 'openclaw waste bot').toUpperCase();
  const engaged = claimed.length + blocked + completed;

  return (
    <section className="console-card console-side-panel p-5" aria-label="Bot activity">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Core Engine</p>
          <h2 className="editorial-title console-side-title text-[var(--text-primary)]">{engineName}</h2>
        </div>
        <span className={`status-chip ${botConnected ? 'status-approved' : 'status-neutral'}`}>
          {botConnected ? 'Stable' : 'Offline'}
        </span>
      </div>

      <div className="console-inset console-engine-card p-4">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <div className="section-label">Current posture</div>
            <div className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">
              {botConnected
                ? 'External bot is choosing waste actions, checking them against guardrails, and posting company outcomes back.'
                : 'No external bot is currently connected to disposal intake.'}
            </div>
          </div>
          <div className="text-right">
            <div className="section-label !text-[0.58rem]">Orders engaged</div>
            <div className="display-number text-[2rem] leading-none text-[var(--text-primary)]">{engaged}</div>
          </div>
        </div>

        <div className="console-engine-stats mt-4">
          <div>
            <div className="section-label !text-[0.6rem]">Claimed</div>
            <div className="mt-1 text-[var(--text-primary)]">{claimed.length}</div>
          </div>
          <div>
            <div className="section-label !text-[0.6rem]">Blocked</div>
            <div className="mt-1 text-[var(--text-primary)]">{blocked}</div>
          </div>
          <div>
            <div className="section-label !text-[0.6rem]">Completed</div>
            <div className="mt-1 text-[var(--text-primary)]">{completed}</div>
          </div>
        </div>
      </div>

      {!botConnected ? (
        <div className="console-inset console-side-empty mt-4 flex flex-col items-center justify-center py-6 text-[var(--text-secondary)]">
          <Bot className="mb-2 h-8 w-8 opacity-40" />
          <p className="text-sm italic">Orders are waiting until a bot claims them.</p>
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          {claimed.length === 0 ? (
            <div className="console-inset console-side-empty flex flex-col items-center justify-center py-6 text-[var(--text-secondary)]">
              <Bot className="mb-2 h-8 w-8 opacity-40" />
              <p className="text-sm italic">Bot connected, but no active disposal decisions right now.</p>
            </div>
          ) : (
            <div>
              <button
                type="button"
                className="bot-activity-accordion-toggle"
                onClick={() => setActivityExpanded((current) => !current)}
                aria-expanded={activityExpanded}
              >
                <div className="bot-activity-dot-strip" aria-hidden="true">
                  {claimed.map((order) => (
                    <span key={order.order_id} className="pulse-dot pulse-dot-compact" />
                  ))}
                </div>
                <div className="bot-activity-accordion-copy">
                  <span className="section-label !mb-0">Orders In Progress</span>
                  <span className="text-xs text-[var(--text-secondary)]">{claimed.length} active</span>
                </div>
                <ChevronDown className={`bot-activity-accordion-chevron ${activityExpanded ? 'bot-activity-accordion-chevron-open' : ''}`} />
              </button>

              {activityExpanded && (
                <div className="console-side-list mt-3 space-y-2">
                  {claimed.map((order) => (
                    <div key={order.order_id} className="console-inset flex items-center justify-between px-3 py-3">
                      <div className="flex items-center gap-2">
                        <span className="pulse-dot" />
                        <span className="text-sm font-medium text-[var(--text-primary)]">{order.declared_waste_type}</span>
                        <span className="text-xs text-[var(--text-secondary)]">{order.quantity_m3.toFixed(1)} m3</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                        {order.assigned_to && <span>{order.assigned_to}</span>}
                        <span className="section-label !text-[0.62rem] !tracking-[0.12em]">{elapsed(order.created_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="bot-activity-history-grid">
            <DecisionColumn
              title="Recent Approved"
              orders={recentApproved}
              emptyMessage="No approved orders yet."
              outcome="approved"
            />
            <DecisionColumn
              title="Recent Rejected"
              orders={recentRejected}
              emptyMessage="No rejected orders yet."
              outcome="rejected"
            />
            <PendingApprovalColumn
              title="Recent Pending Approvals"
              approvals={recentPending}
              emptyMessage="No pending approvals right now."
            />
          </div>
        </div>
      )}
    </section>
  );
}

function PendingApprovalColumn({
  title,
  approvals,
  emptyMessage,
}: {
  title: string;
  approvals: ApprovalItemDTO[];
  emptyMessage: string;
}) {
  return (
    <div className="console-inset bot-decision-column p-3">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="section-label !mb-0">{title}</span>
        <span className="status-chip status-pending">{approvals.length}</span>
      </div>
      {approvals.length === 0 ? (
        <p className="text-xs text-[var(--text-secondary)]">{emptyMessage}</p>
      ) : (
        <div className="space-y-2">
          {approvals.map((approval) => (
            <div key={approval.request_id} className="bot-decision-item">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-[var(--text-primary)]">{approval.title}</div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-[var(--text-secondary)]">
                    <span>{approval.bot_action.replace(/_/g, ' ')}</span>
                    <span>{approval.matched_rules.length} guardrail{approval.matched_rules.length === 1 ? '' : 's'}</span>
                  </div>
                </div>
                <span className="section-label !text-[0.62rem] !tracking-[0.12em]">{elapsed(approval.created_at)}</span>
              </div>
              <p className="mt-2 text-xs leading-5 text-[var(--text-primary)]">"{approval.customer_request}"</p>
              {approval.decision_summary && <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">{approval.decision_summary}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DecisionColumn({
  title,
  orders,
  emptyMessage,
  outcome,
}: {
  title: string;
  orders: DisposalOrderDTO[];
  emptyMessage: string;
  outcome: 'approved' | 'rejected';
}) {
  return (
    <div className="console-inset bot-decision-column p-3">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="section-label !mb-0">{title}</span>
        <span className={`status-chip ${outcome === 'approved' ? 'status-approved' : 'status-rejected'}`}>{orders.length}</span>
      </div>
      {orders.length === 0 ? (
        <p className="text-xs text-[var(--text-secondary)]">{emptyMessage}</p>
      ) : (
        <div className="space-y-2">
          {orders.map((order) => (
            <div key={order.order_id} className="bot-decision-item">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-[var(--text-primary)]">{order.title}</div>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-[var(--text-secondary)]">
                    <span>{order.bot_action?.replace(/_/g, ' ') ?? 'unknown action'}</span>
                    <span>{order.declared_waste_type}</span>
                    <span>{order.quantity_m3.toFixed(1)} m3</span>
                  </div>
                </div>
                <span className="section-label !text-[0.62rem] !tracking-[0.12em]">{elapsed(order.created_at)}</span>
              </div>
              {order.decision_summary && <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">{order.decision_summary}</p>}
              {order.resolution && <p className="mt-2 text-xs leading-5 text-[var(--text-primary)]">{order.resolution}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
