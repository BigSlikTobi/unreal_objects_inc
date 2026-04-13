import { AlertTriangle, Bot, Coins, Factory, RefreshCcw } from 'lucide-react';
import type { CompanyStatus, EconomicsSnapshot } from '../types';
import type { ReactNode } from 'react';

interface Props {
  status: CompanyStatus | null;
  economics: EconomicsSnapshot | null;
  pricingReferenceCount: number;
}

function money(value: number | null | undefined): string {
  if (value == null) return '—';
  const rounded = Math.round(value);
  return `${rounded < 0 ? '-' : ''}€${Math.abs(rounded)}`;
}

function KpiCard({
  label,
  value,
  icon,
  footnote,
}: {
  label: string;
  value: number | string;
  icon: ReactNode;
  footnote: string;
}) {
  return (
    <div className="console-card kpi-card">
      <div className="kpi-card-head">
        <span className="section-label">{label}</span>
        <div className="text-[var(--text-secondary)]">{icon}</div>
      </div>
      <p className="display-number text-5xl leading-none text-[var(--text-primary)]">{value}</p>
      <div className="kpi-card-foot">{footnote}</div>
    </div>
  );
}

export function KpiStrip({ status, economics, rulesCount, pricingReferenceCount }: Props) {
  const stats = status?.stats;

  return (
    <div className="kpi-grid">
      <KpiCard
        label="Cash"
        value={money(economics?.cash_balance_eur)}
        icon={<Coins className="h-5 w-5" />}
        footnote={`Receivables ${money(economics?.accounts_receivable_eur)} vs payables ${money(economics?.accounts_payable_eur)}`}
      />
      <KpiCard
        label="Open Orders"
        value={stats?.open_orders ?? '—'}
        icon={<Factory className="h-5 w-5" />}
        footnote={`${stats?.active_containers ?? 0} active containers in the yard`}
      />
      <KpiCard
        label="Claimed Orders"
        value={stats?.claimed_orders ?? '—'}
        icon={<Bot className="h-5 w-5" />}
        footnote={`${status?.bot_connected ? (status.bot_identity ?? 'Bot connected') : 'No active bot claims right now'}`}
      />
      <KpiCard
        label="Extra Capacity"
        value={stats?.rented_extra_containers ?? '—'}
        icon={<Factory className="h-5 w-5" />}
        footnote={`${stats?.active_containers ?? 0} active containers total`}
      />
      <KpiCard
        label="Pricing References"
        value={pricingReferenceCount}
        icon={<Coins className="h-5 w-5" />}
        footnote="Market quotes and operational options"
      />
      <KpiCard
        label="Overflows"
        value={stats?.overflow_count ?? '—'}
        icon={<AlertTriangle className="h-5 w-5" />}
        footnote={`${stats?.blocked_orders ?? 0} actions currently blocked by guardrails`}
      />
      <KpiCard
        label="Bankruptcies"
        value={stats?.bankruptcy_count ?? '—'}
        icon={<RefreshCcw className="h-5 w-5" />}
        footnote={`Company run #${status?.current_run_id ?? 1}`}
      />
    </div>
  );
}
