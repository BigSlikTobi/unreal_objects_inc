import type { EconomicsSnapshot } from '../types';

interface Props {
  economics: EconomicsSnapshot | null;
}

function money(value: number | null | undefined): string {
  if (value == null) return '—';
  const rounded = Math.round(value);
  return `${rounded < 0 ? '-' : ''}€${Math.abs(rounded)}`;
}

function ledgerValueClass(kind: 'positive' | 'cost' | 'balance', value: number | null | undefined): string {
  if (value == null) return 'text-[var(--text-primary)]';
  if (kind === 'positive') return 'text-[var(--teal)]';
  if (kind === 'cost') return 'text-[var(--red)]';
  return value >= 0 ? 'text-[var(--teal)]' : 'text-[var(--red)]';
}

export function EconomicsPanel({ economics }: Props) {
  return (
    <section className="console-card console-side-panel p-5" aria-label="Economics">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Economics</p>
          <h2 className="editorial-title console-side-title text-[var(--text-primary)]">Company Ledger</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Cash, invoices, liabilities, and current company run.
          </p>
        </div>
        <span className="ghost-pill">Run #{economics?.current_run_id ?? 1}</span>
      </div>

      <div className="console-inset mt-4 space-y-3 p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Cash In</span>
          <span className={ledgerValueClass('positive', economics?.revenue_eur)}>{money(economics?.revenue_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Invoiced Revenue</span>
          <span className={ledgerValueClass('positive', economics?.invoiced_revenue_eur)}>{money(economics?.invoiced_revenue_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Accounts Receivable</span>
          <span className={ledgerValueClass('positive', economics?.accounts_receivable_eur)}>{money(economics?.accounts_receivable_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Accounts Payable</span>
          <span className={ledgerValueClass('cost', economics?.accounts_payable_eur)}>{money(economics?.accounts_payable_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Operating Cost</span>
          <span className={ledgerValueClass('cost', economics?.operating_cost_eur)}>{money(economics?.operating_cost_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Pickup & Exchange Cost</span>
          <span className={ledgerValueClass('cost', economics?.rental_cost_eur)}>{money(economics?.rental_cost_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Overhead Cost</span>
          <span className={ledgerValueClass('cost', economics?.overhead_cost_eur)}>{money(economics?.overhead_cost_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Penalty Cost</span>
          <span className={ledgerValueClass('cost', economics?.penalty_cost_eur)}>{money(economics?.penalty_cost_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Penalty Avoided</span>
          <span className={ledgerValueClass('positive', economics?.overflow_penalty_avoided_eur)}>{money(economics?.overflow_penalty_avoided_eur)}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Early Empty Cost</span>
          <span className={ledgerValueClass('cost', economics?.early_empty_cost_eur)}>{money(economics?.early_empty_cost_eur)}</span>
        </div>
        <div className="h-px bg-[rgba(122,146,183,0.14)]" />
        <div className="flex items-center justify-between">
          <span className="section-label">Cash Balance</span>
          <span className={`display-number text-2xl ${ledgerValueClass('balance', economics?.cash_balance_eur)}`}>{money(economics?.cash_balance_eur)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="section-label">Realized Profit</span>
          <span className={`display-number text-2xl ${ledgerValueClass('balance', economics?.profit_eur)}`}>{money(economics?.profit_eur)}</span>
        </div>
      </div>
    </section>
  );
}
