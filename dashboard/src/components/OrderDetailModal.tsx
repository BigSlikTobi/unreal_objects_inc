import { X } from 'lucide-react';
import type { DisposalOrderDTO } from '../types';
import { OrderEconomicsPanel } from './OrderEconomicsPanel';

interface Props {
  order: DisposalOrderDTO;
  onClose: () => void;
}

const STATUS_BADGE: Record<string, { chipClass: string }> = {
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

function money(value: number | null): string {
  return value == null ? '—' : `€${value.toFixed(0)}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function OrderDetailModal({ order, onClose }: Props) {
  const statusConfig = STATUS_BADGE[order.status] ?? STATUS_BADGE.open;

  return (
    <div className="order-modal-backdrop" onClick={onClose} aria-label="Close order detail">
      <div
        className="order-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={`Order ${order.order_id.slice(0, 8)} detail`}
      >
        {/* Modal header */}
        <div className="order-modal-header">
          <div>
            <span className="order-cell-id" style={{ fontSize: '0.8125rem' }}>
              {order.order_id.slice(0, 8)}
            </span>
            <h2 className="order-modal-title">{order.title}</h2>
          </div>
          <button
            type="button"
            className="order-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal body */}
        <div className="order-modal-body">
          {/* Status + priority row */}
          <div className="order-modal-badges">
            <span className={statusConfig.chipClass}>
              <span className="status-badge-dot" aria-hidden="true" />
              {order.status}
            </span>
            <span className={PRIORITY_BADGE[order.priority] ?? PRIORITY_BADGE.standard}>
              <span className="status-badge-dot" aria-hidden="true" />
              {order.priority}
            </span>
            {order.hazardous_flag && (
              <span className="status-badge status-badge-red">
                <span className="status-badge-dot" aria-hidden="true" />
                Hazardous
              </span>
            )}
            {order.contamination_risk && (
              <span className="status-badge status-badge-amber">
                <span className="status-badge-dot" aria-hidden="true" />
                Contamination risk
              </span>
            )}
          </div>

          {/* Customer request */}
          <div className="console-inset order-modal-section">
            <p className="section-label" style={{ marginBottom: '0.25rem' }}>
              Customer Request
            </p>
            <p style={{ color: 'var(--text-primary)', fontSize: '0.8125rem' }}>
              "{order.customer_request}"
            </p>
          </div>

          {/* Key metrics */}
          <div className="order-modal-metrics">
            <div className="order-modal-metric">
              <span className="section-label">Waste Type</span>
              <span className="order-modal-metric-value">{order.declared_waste_type}</span>
            </div>
            <div className="order-modal-metric">
              <span className="section-label">Volume</span>
              <span className="order-modal-metric-value">{order.quantity_m3.toFixed(1)} m³</span>
            </div>
            <div className="order-modal-metric">
              <span className="section-label">Offered Price</span>
              <span className="order-modal-metric-value">{money(order.offered_price_eur)}</span>
            </div>
            <div className="order-modal-metric">
              <span className="section-label">Service Window</span>
              <span className="order-modal-metric-value">{order.service_window.replace('_', ' ')}</span>
            </div>
            <div className="order-modal-metric">
              <span className="section-label">Created</span>
              <span className="order-modal-metric-value">{formatTime(order.created_at)}</span>
            </div>
            {order.assigned_to && (
              <div className="order-modal-metric">
                <span className="section-label">Assigned To</span>
                <span className="order-modal-metric-value">{order.assigned_to}</span>
              </div>
            )}
          </div>

          {/* Bot action */}
          {order.bot_action && (
            <div className="console-inset order-modal-section">
              <p className="section-label" style={{ marginBottom: '0.25rem' }}>
                Bot Action
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className="ghost-pill">{order.bot_action.replace(/_/g, ' ')}</span>
                <span className="ghost-pill">{order.decision_outcome || 'Awaiting decision'}</span>
              </div>
            </div>
          )}

          {/* Economics */}
          <OrderEconomicsPanel
            baseline={order.baseline_economics}
            projected={order.projected_action_economics}
          />

          {/* Decision summary */}
          {order.decision_summary && (
            <div className="console-inset order-modal-section">
              <p className="section-label" style={{ marginBottom: '0.25rem' }}>
                Bot Decision
              </p>
              <p style={{ color: 'var(--text-primary)', fontSize: '0.8125rem' }}>
                {order.decision_summary}
              </p>
            </div>
          )}

          {/* Matched rules */}
          {order.matched_rules.length > 0 && (
            <div className="order-modal-section">
              <p className="section-label" style={{ marginBottom: '0.375rem' }}>
                Matched Rules
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                {order.matched_rules.map((rule) => (
                  <span key={rule} className="feed-rule-pill">
                    {rule}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Resolution */}
          {order.resolution && (
            <div className="order-modal-section">
              <p className="section-label" style={{ marginBottom: '0.25rem' }}>
                Resolution
              </p>
              <p style={{ color: 'var(--text-primary)', fontSize: '0.8125rem', fontWeight: 500 }}>
                {order.resolution}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
