import { useEffect, useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { DisposalOrderDTO } from '../types';
import { OrderDetailModal } from './OrderDetailModal';

interface Props {
  orders: DisposalOrderDTO[];
}

const PAGE_SIZE = 15;

const STATUS_BADGE: Record<string, { chipClass: string }> = {
  open:      { chipClass: 'status-badge status-badge-blue' },
  claimed:   { chipClass: 'status-badge status-badge-neutral' },
  blocked:   { chipClass: 'status-badge status-badge-amber' },
  completed: { chipClass: 'status-badge status-badge-green' },
  rejected:  { chipClass: 'status-badge status-badge-red' },
};

type StatusFilter = 'all' | 'open' | 'claimed' | 'blocked' | 'completed' | 'rejected';

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

export function CaseFeed({ orders }: Props) {
  const [page, setPage] = useState(0);
  const [selectedOrder, setSelectedOrder] = useState<DisposalOrderDTO | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const filtered = useMemo(() => {
    const sorted = [...orders].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    if (statusFilter === 'all') return sorted;
    return sorted.filter((o) => o.status === statusFilter);
  }, [orders, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageOrders = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // Reset page when filter changes or orders shrink
  useEffect(() => {
    setPage(0);
  }, [statusFilter]);

  // Clamp page if orders shrink
  useEffect(() => {
    if (page >= totalPages) setPage(Math.max(0, totalPages - 1));
  }, [page, totalPages]);

  // Close modal on Escape
  useEffect(() => {
    if (!selectedOrder) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setSelectedOrder(null);
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [selectedOrder]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const o of orders) {
      counts[o.status] = (counts[o.status] ?? 0) + 1;
    }
    return counts;
  }, [orders]);

  return (
    <section className="view-page flex min-h-0 flex-col" aria-label="Disposal orders">
      {/* Header */}
      <div className="order-list-header">
        <div>
          <p className="console-panel-kicker">Live Intake</p>
          <h2 className="console-panel-title">Disposal Orders</h2>
        </div>
        <div className="console-panel-actions">
          <span className="ghost-pill">{filtered.length} orders</span>
        </div>
      </div>

      {/* Filter bar */}
      <div className="order-filter-bar">
        {(['all', 'open', 'claimed', 'blocked', 'completed', 'rejected'] as StatusFilter[]).map(
          (f) => {
            const count = f === 'all' ? orders.length : (statusCounts[f] ?? 0);
            return (
              <button
                key={f}
                type="button"
                className={`order-filter-chip ${statusFilter === f ? 'order-filter-chip-active' : ''}`}
                onClick={() => setStatusFilter(f)}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                <span className="order-filter-count">{count}</span>
              </button>
            );
          },
        )}
      </div>

      {/* Table + Pagination — grouped in a single card surface */}
      <div className="view-data-card">
        <div className="order-table-wrap">
          <table className="order-table" role="grid">
            <thead>
              <tr>
                <th>Order</th>
                <th>Waste</th>
                <th className="order-col-hide-mobile">Volume</th>
                <th className="order-col-hide-mobile">Price</th>
                <th>Status</th>
                <th className="order-col-hide-mobile">Time</th>
              </tr>
            </thead>
            <tbody>
              {pageOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="order-table-empty">
                    No orders match this filter.
                  </td>
                </tr>
              ) : (
                pageOrders.map((order) => {
                  const badge = STATUS_BADGE[order.status] ?? STATUS_BADGE.open;
                  return (
                    <tr
                      key={order.order_id}
                      className="order-table-row"
                      onClick={() => setSelectedOrder(order)}
                    >
                      <td>
                        <button
                          type="button"
                          className="order-cell-primary"
                          onClick={(e) => { e.stopPropagation(); setSelectedOrder(order); }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              setSelectedOrder(order);
                            } else if (e.key === ' ') {
                              e.preventDefault();
                              setSelectedOrder(order);
                            }
                          }}
                          aria-label={`View order ${order.order_id.slice(0, 8)}`}
                        >
                          <span className="order-cell-id">{order.order_id.slice(0, 8)}</span>
                          <span className="order-cell-title">{order.title}</span>
                        </button>
                      </td>
                      <td>
                        <span className="ghost-pill">{order.declared_waste_type}</span>
                      </td>
                      <td className="order-col-hide-mobile">{order.quantity_m3.toFixed(1)} m³</td>
                      <td className="order-col-hide-mobile">{money(order.offered_price_eur)}</td>
                      <td>
                        <span className={badge.chipClass}>
                          <span className="status-badge-dot" aria-hidden="true" />
                          {order.status}
                        </span>
                      </td>
                      <td className="order-col-hide-mobile">{timeAgo(order.created_at)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="order-pagination">
        <span className="order-pagination-info">
          {filtered.length === 0
            ? 'No orders'
            : `${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, filtered.length)} of ${filtered.length}`}
        </span>
        <div className="order-pagination-buttons">
          <button
            type="button"
            className="order-page-btn"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="order-page-indicator">
            {page + 1} / {totalPages}
          </span>
          <button
            type="button"
            className="order-page-btn"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
      </div>

      {/* Detail modal */}
      {selectedOrder && (
        <OrderDetailModal
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
        />
      )}
    </section>
  );
}
