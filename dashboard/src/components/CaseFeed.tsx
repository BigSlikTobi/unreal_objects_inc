import type { DisposalOrderDTO } from '../types';
import { CaseCard } from './CaseCard';

interface Props {
  orders: DisposalOrderDTO[];
}

export function CaseFeed({ orders }: Props) {
  const sorted = [...orders]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 50);

  return (
    <section className="console-card flex min-h-0 flex-col p-5" aria-label="Live order feed">
      <div className="console-panel-header">
        <div>
          <p className="console-panel-kicker">Live Intake</p>
          <h2 className="console-panel-title">Disposal Orders</h2>
        </div>
        <div className="console-panel-actions">
          <span className="ghost-pill">Waste Ops</span>
          <span className="ghost-pill">{sorted.length} visible</span>
        </div>
      </div>
      <div className="feed-scroll">
        <div className="feed-stack">
          {sorted.length === 0 ? (
            <div className="console-inset px-4 py-8 text-sm italic text-[var(--text-secondary)]">
              No disposal orders yet...
            </div>
          ) : (
            sorted.map((order) => <CaseCard key={order.order_id} c={order} />)
          )}
        </div>
      </div>
    </section>
  );
}
