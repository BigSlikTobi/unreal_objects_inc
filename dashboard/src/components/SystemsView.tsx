import type { CompanyStatus, PricingCatalogResponse } from '../types';

interface Props {
  apiHealthy: boolean;
  botConnected: boolean;
  status: CompanyStatus | null;
  pricing: PricingCatalogResponse | null;
}

export function SystemsView({ apiHealthy, botConnected, status, pricing }: Props) {
  const systemRows = [
    { label: 'Company API', value: apiHealthy ? 'Online' : 'Offline', state: apiHealthy ? 'healthy' : 'idle' },
    { label: 'External Bot', value: botConnected ? 'Connected' : 'Offline', state: botConnected ? 'healthy' : 'idle' },
    { label: 'Deployment', value: status?.deployment_mode ?? 'local', state: 'info' },
    { label: 'Pricing Catalog', value: `${(pricing?.market_quotes.length ?? 0) + (pricing?.operational_options.length ?? 0)} entries`, state: 'info' },
    { label: 'Persistence', value: status?.persistence_backend ?? 'memory', state: 'info' },
    { label: 'Current Run', value: `#${status?.current_run_id ?? 1}`, state: 'healthy' },
  ];

  return (
    <div className="console-view-stack">
      <section className="console-card p-5">
        <div className="console-panel-header">
          <div>
            <p className="console-panel-kicker">Systems</p>
            <h2 className="console-side-title editorial-title text-[var(--text-primary)]">Runtime Nodes</h2>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Connectivity and live operating surfaces across the company stack.
            </p>
          </div>
          <span className="ghost-pill">{apiHealthy ? 'healthy' : 'partial'}</span>
        </div>
        <div className="console-inset mt-4 grid gap-3 p-4 sm:grid-cols-2">
          {systemRows.map((row) => (
            <div key={row.label} className="overview-stat">
              <span className="section-label">{row.label}</span>
              <span className="overview-stat-value systems-stat-value">{row.value}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
