import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { DisposalOrderDTO } from '../types';
import { OrderEconomicsPanel } from './OrderEconomicsPanel';

interface Props {
  c: DisposalOrderDTO;
}

const PRIORITY_COLORS: Record<string, string> = {
  standard: 'bg-[rgba(35,78,166,0.28)] text-[var(--primary)]',
  urgent: 'bg-[rgba(164,45,52,0.33)] text-[var(--error)]',
};

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-[rgba(35,78,166,0.28)] text-[var(--primary)]',
  claimed: 'bg-[rgba(23,51,100,0.55)] text-[var(--text-primary)]',
  blocked: 'bg-[rgba(131,79,10,0.32)] text-[var(--amber)]',
  completed: 'bg-[rgba(32,122,93,0.32)] text-[var(--tertiary)]',
  rejected: 'bg-[rgba(164,45,52,0.33)] text-[var(--error)]',
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function money(value: number | null): string {
  return value == null ? '—' : `€${value.toFixed(0)}`;
}

function cardClass(order: DisposalOrderDTO): string {
  if (order.status === 'blocked') return 'feed-card feed-card-high';
  if (order.priority === 'urgent') return 'feed-card feed-card-urgent';
  if (order.status === 'completed') return 'feed-card feed-card-resolved';
  if (order.status === 'rejected') return 'feed-card feed-card-urgent';
  return 'feed-card';
}

export function CaseCard({ c }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`${cardClass(c)} relative cursor-pointer ${expanded ? 'z-10' : ''}`}
      onClick={() => setExpanded(!expanded)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setExpanded(!expanded); }}
      aria-expanded={expanded}
    >
      <div className="feed-card-inner">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <button
              type="button"
              className="feed-card-toggle"
              onClick={(event) => {
                event.stopPropagation();
                setExpanded(!expanded);
              }}
              aria-label={expanded ? 'Collapse order details' : 'Expand order details'}
            >
              {expanded ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
            </button>
            <div className="flex min-w-0 flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`status-chip ${PRIORITY_COLORS[c.priority] || PRIORITY_COLORS.standard}`}>
                  {c.priority}
                </span>
                <span className="ghost-pill">{c.declared_waste_type}</span>
                <span className="ghost-pill">{c.quantity_m3.toFixed(1)} m3</span>
              </div>
              <div>
                <div className="editorial-title feed-card-title">{c.title}</div>
                <p className="feed-card-body">"{c.customer_request}"</p>
              </div>
            </div>
          </div>

          <div className="feed-card-meta">
            <span className="feed-card-id">ID: {c.order_id.slice(0, 8)}</span>
            <span className={`status-chip ${STATUS_COLORS[c.status] || STATUS_COLORS.open}`}>{c.status}</span>
          </div>
        </div>

        <div className="feed-card-footer">
          <div className="feed-card-footer-left">
            <span className="feed-card-footer-item">{timeAgo(c.created_at)}</span>
            <span className="feed-card-footer-item">{money(c.offered_price_eur)}</span>
            {c.baseline_economics && (
              <span className={`feed-card-footer-item ${c.baseline_economics.baseline_margin_eur >= 0 ? 'text-[var(--tertiary)]' : 'text-[var(--error)]'}`}>
                margin {money(c.baseline_economics.baseline_margin_eur)}
              </span>
            )}
            <span className="feed-card-footer-item">{c.service_window.replace('_', ' ')}</span>
            {c.assigned_to && <span className="feed-card-footer-item">{c.assigned_to}</span>}
          </div>
          <div className="feed-card-footer-right">
            {c.bot_action && <span className="feed-card-inline-label">{c.bot_action.replace(/_/g, ' ')}</span>}
            <span className="ghost-pill">{c.decision_outcome || 'Awaiting bot decision'}</span>
          </div>
        </div>

        <OrderEconomicsPanel baseline={c.baseline_economics} projected={c.projected_action_economics} compact />

        {expanded && (
          <div className="mt-4 text-xs">
            <div className="feed-detail-block space-y-3">
              <div className="console-inset px-3 py-3 text-[var(--text-secondary)]">
                <p className="section-label !mb-1">Customer Request</p>
                <p className="text-[var(--text-primary)]">"{c.customer_request}"</p>
              </div>
              <div className="metric-row">
                <span className="metric-label">Waste: <strong className="metric-value">{c.declared_waste_type}</strong></span>
                <span className="metric-label">Volume: <strong className="metric-value">{c.quantity_m3.toFixed(1)} m3</strong></span>
                <span className="metric-label">Revenue: <strong className="metric-value">{money(c.offered_price_eur)}</strong></span>
                <span className="metric-label">Priority: <strong className="metric-value">{c.priority}</strong></span>
                {c.bot_action && <span className="metric-label">Bot Action: <strong className="metric-value">{c.bot_action}</strong></span>}
              </div>
              <OrderEconomicsPanel baseline={c.baseline_economics} projected={c.projected_action_economics} />
              {c.decision_summary && (
                <div className="console-inset px-3 py-3 text-[var(--text-secondary)]">
                  <p className="section-label !mb-1">Bot Decision</p>
                  <p className="text-[var(--text-primary)]">{c.decision_summary}</p>
                </div>
              )}
              {c.matched_rules.length > 0 && (
                <div className="feed-rule-row">
                  {c.matched_rules.map((rule) => (
                    <span key={rule} className="feed-rule-pill">{rule}</span>
                  ))}
                </div>
              )}
              {c.resolution && (
                <p className="text-[var(--text-secondary)]">Resolution: <strong className="metric-value">{c.resolution}</strong></p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
