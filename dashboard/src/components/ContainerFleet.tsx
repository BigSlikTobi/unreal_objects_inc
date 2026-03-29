import type { ContainerDTO } from '../types';

interface Props {
  containers: ContainerDTO[];
}

function timeUntil(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now();
  const mins = Math.floor(diff / 60000);
  if (mins <= 0) return 'due now';
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

export function ContainerFleet({ containers }: Props) {
  return (
    <section className="console-card console-side-panel p-5" aria-label="Container fleet">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Container Fleet</p>
          <h2 className="editorial-title console-side-title text-[var(--text-primary)]">Yard Capacity</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Fill levels, next emptying, and exchange cost per pickup.
          </p>
        </div>
        <span className="ghost-pill">{containers.length} live</span>
      </div>

      <div className="console-side-list mt-4 space-y-3">
        {containers.map((container) => (
          <div key={container.container_id} className="console-inset px-4 py-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-[var(--text-primary)]">{container.label}</div>
                <div className="text-xs text-[var(--text-secondary)]">{container.waste_type}</div>
              </div>
              <div className="text-right text-xs text-[var(--text-secondary)]">
                <div>{container.fill_level_m3.toFixed(1)} / {container.capacity_m3.toFixed(1)} m3</div>
                <div>{timeUntil(container.next_empty_at)}</div>
              </div>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[rgba(2,8,19,0.95)]">
              <div
                className={`${container.overflowed ? 'bg-red-500' : 'bg-[linear-gradient(90deg,#79a6ff,#74e3c4)]'} h-full rounded-full`}
                style={{ width: `${Math.min(container.fill_ratio * 100, 100)}%` }}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {container.is_rented_extra && <span className="ghost-pill">Extra Capacity</span>}
              {container.overflowed && <span className="status-chip status-rejected">Overflowed</span>}
              <span className="ghost-pill">€{container.rental_cost_per_cycle_eur.toFixed(0)}/exchange</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
