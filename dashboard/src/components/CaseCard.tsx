import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { DisposalOrderDTO } from '../types';
import { OrderEconomicsPanel } from './OrderEconomicsPanel';

interface Props {
  c: DisposalOrderDTO;
}

const STATUS_BADGE: Record<
  string,
  { chipClass: string; label?: string }
> = {
  open:      { chipClass: 'status-badge status-badge-blue' },
  claimed:   { chipClass: 'status-badge status-badge-neutral' },
  blocked:   { chipClass: 'status-badge status-badge-amber' },
  completed: { chipClass: 'status-badge status-badge-green' },
  rejected:  { chipClass: 'status-badge status-badge-red' },
};

const PRIORITY_BADGE: Record<string, string> = {
  standard: 'status-badge status-badge-blue',
  urgent:   'status-badge status-badge-red',
};

function cardBorderColor(order: DisposalOrderDTO): string {
  if (order.status === 'blocked') return 'var(--amber)';
  if (order.priority === 'urgent' || order.status === 'rejected') return 'var(--red)';
  if (order.status === 'completed') return 'var(--green)';
  return 'var(--blue)';
}

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

export function CaseCard({ c }: Props) {
  const [expanded, setExpanded] = useState(false);
  const statusConfig = STATUS_BADGE[c.status] ?? STATUS_BADGE.open;

  return (
    <div
      className="feed-card"
      style={{ borderLeftColor: cardBorderColor(c) }}
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      onClick={() => setExpanded(!expanded)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') setExpanded(!expanded);
      }}
    >
      <div className="feed-card-inner">
        {/* Top row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '0.75rem',
            marginBottom: '0.5rem',
          }}
        >
          {/* Left: toggle + content */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', minWidth: 0 }}>
            <button
              type="button"
              className="feed-card-toggle"
              onClick={(e) => {
                e.stopPropagation();
                setExpanded(!expanded);
              }}
              aria-label={expanded ? 'Collapse order details' : 'Expand order details'}
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4 shrink-0" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0" aria-hidden="true" />
              )}
            </button>

            <div style={{ minWidth: 0 }}>
              {/* Badges row */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  gap: '0.375rem',
                  marginBottom: '0.375rem',
                }}
              >
                <span className={PRIORITY_BADGE[c.priority] ?? PRIORITY_BADGE.standard}>
                  <span className="status-badge-dot" aria-hidden="true" />
                  {c.priority}
                </span>
                <span className="ghost-pill">{c.declared_waste_type}</span>
                <span className="ghost-pill">{c.quantity_m3.toFixed(1)} m³</span>
              </div>
              {/* Title */}
              <div className="feed-card-title">{c.title}</div>
              <p className="feed-card-body">"{c.customer_request}"</p>
            </div>
          </div>

          {/* Right: id + status */}
          <div className="feed-card-meta">
            <span className="feed-card-id" aria-label={`Order ID: ${c.order_id.slice(0, 8)}`}>
              {c.order_id.slice(0, 8)}
            </span>
            <span
              className={statusConfig.chipClass}
              aria-label={`Status: ${c.status}`}
            >
              <span className="status-badge-dot" aria-hidden="true" />
              {c.status}
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className="feed-card-footer">
          <div className="feed-card-footer-left">
            <span className="feed-card-footer-item">{timeAgo(c.created_at)}</span>
            <span className="feed-card-footer-item">{money(c.offered_price_eur)}</span>
            {c.baseline_economics && (
              <span
                className="feed-card-footer-item"
                style={{
                  color:
                    c.baseline_economics.baseline_margin_eur >= 0
                      ? 'var(--green)'
                      : 'var(--red)',
                }}
              >
                margin {money(c.baseline_economics.baseline_margin_eur)}
              </span>
            )}
            <span className="feed-card-footer-item">
              {c.service_window.replace('_', ' ')}
            </span>
            {c.assigned_to && (
              <span className="feed-card-footer-item">{c.assigned_to}</span>
            )}
          </div>
          <div className="feed-card-footer-right">
            {c.bot_action && (
              <span className="feed-card-inline-label">
                {c.bot_action.replace(/_/g, ' ')}
              </span>
            )}
            <span className="ghost-pill">
              {c.decision_outcome || 'Awaiting decision'}
            </span>
          </div>
        </div>

        {/* Compact economics */}
        <OrderEconomicsPanel
          baseline={c.baseline_economics}
          projected={c.projected_action_economics}
          compact
        />

        {/* Expanded detail */}
        {expanded && (
          <div style={{ marginTop: '0.75rem' }}>
            <div className="feed-detail-block">
              <div
                className="console-inset"
                style={{ padding: '0.625rem 0.75rem', marginBottom: '0.625rem' }}
              >
                <p className="section-label" style={{ marginBottom: '0.25rem' }}>
                  Customer Request
                </p>
                <p style={{ color: 'var(--text-primary)', fontSize: '0.8125rem' }}>
                  "{c.customer_request}"
                </p>
              </div>
              <div className="metric-row" style={{ marginBottom: '0.625rem' }}>
                <span className="metric-label">
                  Waste:{' '}
                  <strong className="metric-value">{c.declared_waste_type}</strong>
                </span>
                <span className="metric-label">
                  Volume:{' '}
                  <strong className="metric-value">{c.quantity_m3.toFixed(1)} m³</strong>
                </span>
                <span className="metric-label">
                  Revenue:{' '}
                  <strong className="metric-value">{money(c.offered_price_eur)}</strong>
                </span>
                <span className="metric-label">
                  Priority:{' '}
                  <strong className="metric-value">{c.priority}</strong>
                </span>
                {c.bot_action && (
                  <span className="metric-label">
                    Bot Action:{' '}
                    <strong className="metric-value">{c.bot_action}</strong>
                  </span>
                )}
              </div>
              <OrderEconomicsPanel
                baseline={c.baseline_economics}
                projected={c.projected_action_economics}
              />
              {c.decision_summary && (
                <div
                  className="console-inset"
                  style={{ padding: '0.625rem 0.75rem', marginTop: '0.625rem' }}
                >
                  <p className="section-label" style={{ marginBottom: '0.25rem' }}>
                    Bot Decision
                  </p>
                  <p style={{ color: 'var(--text-primary)', fontSize: '0.8125rem' }}>
                    {c.decision_summary}
                  </p>
                </div>
              )}
              {c.matched_rules.length > 0 && (
                <div className="feed-rule-row" style={{ marginTop: '0.625rem' }}>
                  {c.matched_rules.map((rule) => (
                    <span key={rule} className="feed-rule-pill">
                      {rule}
                    </span>
                  ))}
                </div>
              )}
              {c.resolution && (
                <p
                  style={{
                    marginTop: '0.5rem',
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                  }}
                >
                  Resolution:{' '}
                  <strong className="metric-value">{c.resolution}</strong>
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
