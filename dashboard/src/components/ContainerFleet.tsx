import { useMemo } from 'react';
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

function fillColor(container: ContainerDTO): string {
  if (container.overflowed) return 'var(--red)';
  if (container.at_risk) return 'var(--amber)';
  if (container.fill_ratio > 0.75) return 'var(--amber)';
  return 'var(--blue)';
}

function fillColorFaded(container: ContainerDTO): string {
  if (container.overflowed) return 'color-mix(in srgb, var(--red) 15%, transparent)';
  if (container.at_risk) return 'color-mix(in srgb, var(--amber) 15%, transparent)';
  if (container.fill_ratio > 0.75) return 'color-mix(in srgb, var(--amber) 15%, transparent)';
  return 'color-mix(in srgb, var(--blue) 12%, transparent)';
}

function ContainerVisual({ container }: { container: ContainerDTO }) {
  const pct = Math.min(container.fill_ratio * 100, 100);
  const color = fillColor(container);
  const fadedColor = fillColorFaded(container);

  return (
    <div className="container-card" title={`${container.label} — ${container.waste_type}`}>
      {/* Container body */}
      <div className="container-body">
        {/* Fill level */}
        <div
          className="container-fill"
          style={{
            height: `${pct}%`,
            backgroundColor: fadedColor,
            borderTop: pct > 0 ? `2px solid ${color}` : 'none',
          }}
        />

        {/* Content overlay */}
        <div className="container-content">
          <span className="container-pct" style={{ color }}>
            {Math.round(pct)}%
          </span>
          <span className="container-vol">
            {container.fill_level_m3.toFixed(1)}/{container.capacity_m3.toFixed(0)}m³
          </span>
        </div>

        {/* Status indicator */}
        {container.overflowed && <div className="container-status-flag container-flag-overflow">OVERFLOW</div>}
        {container.at_risk && !container.overflowed && <div className="container-status-flag container-flag-risk">AT RISK</div>}
      </div>

      {/* Label underneath */}
      <div className="container-label-area">
        <span className="container-name">{container.label}</span>
        <div className="container-meta">
          <span>empty {timeUntil(container.next_empty_at)}</span>
          {container.is_rented_extra && <span className="container-extra-tag">Extra</span>}
        </div>
      </div>
    </div>
  );
}

export function ContainerFleet({ containers }: Props) {
  const grouped = useMemo(() => {
    const map = new Map<string, ContainerDTO[]>();
    for (const c of containers) {
      const group = map.get(c.waste_type) ?? [];
      group.push(c);
      map.set(c.waste_type, group);
    }
    // Sort groups alphabetically, sort containers within each group by label
    const entries = [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
    for (const [, group] of entries) {
      group.sort((a, b) => a.label.localeCompare(b.label));
    }
    return entries;
  }, [containers]);

  const overflowed = containers.filter((c) => c.overflowed).length;
  const atRisk = containers.filter((c) => c.at_risk && !c.overflowed).length;

  return (
    <section className="view-page flex min-h-0 flex-col" aria-label="Container fleet">
      {/* Header */}
      <div className="container-fleet-header">
        <div>
          <p className="console-panel-kicker">Container Fleet</p>
          <h2 className="console-panel-title">Yard Capacity</h2>
        </div>
        <div className="console-panel-actions">
          {overflowed > 0 && (
            <span className="status-badge status-badge-red">
              <span className="status-badge-dot" aria-hidden="true" />
              {overflowed} overflowed
            </span>
          )}
          {atRisk > 0 && (
            <span className="status-badge status-badge-amber">
              <span className="status-badge-dot" aria-hidden="true" />
              {atRisk} at risk
            </span>
          )}
          <span className="ghost-pill">{containers.length} containers</span>
        </div>
      </div>

      {/* Grouped container yard */}
      <div className="view-data-card container-yard">
        {containers.length === 0 ? (
          <div className="container-yard-empty">
            <p>No containers yet.</p>
          </div>
        ) : (
          grouped.map(([wasteType, group]) => (
            <div key={wasteType} className="container-type-group">
              <div className="container-type-header">
                <span className="container-type-label">{wasteType}</span>
                <span className="container-type-count">{group.length}</span>
              </div>
              <div className="container-grid">
                {group.map((c) => (
                  <ContainerVisual key={c.container_id} container={c} />
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
