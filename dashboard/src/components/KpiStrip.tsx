import { AlertTriangle, Bot, Coins, Factory, Tag } from 'lucide-react';
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

type IconVariant = 'blue' | 'green' | 'amber' | 'red' | 'purple';

function KpiCard({
  label,
  value,
  icon,
  footnote,
  variant = 'blue',
}: {
  label: string;
  value: number | string;
  icon: ReactNode;
  footnote: string;
  variant?: IconVariant;
}) {
  return (
    <div className="console-card kpi-card">
      <div className="kpi-card-head">
        <span className="kpi-card-label">{label}</span>
        <div className={`kpi-icon kpi-icon-${variant}`} aria-hidden="true">
          {icon}
        </div>
      </div>
      <p
        className="display-number"
        style={{ fontSize: '2rem' }}
        aria-label={`${label}: ${value}`}
      >
        {value}
      </p>
      <div className="kpi-card-foot">{footnote}</div>
    </div>
  );
}

export function KpiStrip({ status, economics, pricingReferenceCount }: Props) {
  const stats = status?.stats;

  return (
    <div className="kpi-grid" role="region" aria-label="Key performance indicators">
      <KpiCard
        label="Cash Balance"
        value={money(economics?.cash_balance_eur)}
        icon={<Coins className="h-4 w-4" />}
        footnote={`AR ${money(economics?.accounts_receivable_eur)} · AP ${money(economics?.accounts_payable_eur)}`}
        variant="blue"
      />
      <KpiCard
        label="Open Orders"
        value={stats?.open_orders ?? '—'}
        icon={<Factory className="h-4 w-4" />}
        footnote={`${stats?.active_containers ?? 0} containers active`}
        variant="purple"
      />
      <KpiCard
        label="Claimed Orders"
        value={stats?.claimed_orders ?? '—'}
        icon={<Bot className="h-4 w-4" />}
        footnote={
          status?.bot_connected
            ? (status.bot_identity ?? 'Bot connected')
            : 'No active bot claims'
        }
        variant="green"
      />
      <KpiCard
        label="Extra Capacity"
        value={stats?.rented_extra_containers ?? '—'}
        icon={<Factory className="h-4 w-4" />}
        footnote={`${stats?.active_containers ?? 0} containers total`}
        variant="amber"
      />
      <KpiCard
        label="Pricing References"
        value={pricingReferenceCount}
        icon={<Tag className="h-4 w-4" />}
        footnote="Market quotes and operational options"
        variant="blue"
      />
      <KpiCard
        label="Overflows"
        value={stats?.overflow_count ?? '—'}
        icon={<AlertTriangle className="h-4 w-4" />}
        footnote={`${stats?.blocked_orders ?? 0} actions blocked by guardrails`}
        variant="red"
      />
    </div>
  );
}
