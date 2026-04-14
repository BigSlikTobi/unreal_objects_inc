import type { EconomicsSnapshot } from '../types';

interface Props {
  economics: EconomicsSnapshot | null;
}

function money(value: number | null | undefined): string {
  if (value == null) return '—';
  const rounded = Math.round(value);
  return `${rounded < 0 ? '-' : ''}€${Math.abs(rounded)}`;
}

function ledgerColor(
  kind: 'positive' | 'cost' | 'balance',
  value: number | null | undefined,
): string {
  if (value == null) return 'var(--text-primary)';
  if (kind === 'positive') return 'var(--green)';
  if (kind === 'cost') return 'var(--red)';
  return value >= 0 ? 'var(--green)' : 'var(--red)';
}

interface LedgerRowProps {
  label: string;
  value: number | null | undefined;
  kind: 'positive' | 'cost' | 'balance';
  large?: boolean;
}

function LedgerRow({ label, value, kind, large }: LedgerRowProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: large ? '0.9375rem' : '0.8125rem',
      }}
    >
      <span style={{ color: large ? 'var(--text-secondary)' : 'var(--text-muted)' }}>
        {label}
      </span>
      <span
        style={{
          fontFamily: large ? '"Space Grotesk", sans-serif' : 'inherit',
          fontWeight: large ? 700 : 500,
          fontSize: large ? '1.125rem' : 'inherit',
          color: ledgerColor(kind, value),
          letterSpacing: large ? '-0.02em' : undefined,
        }}
      >
        {money(value)}
      </span>
    </div>
  );
}

export function EconomicsPanel({ economics }: Props) {
  return (
    <section className="console-card console-side-panel p-5" aria-label="Company economics">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Economics</p>
          <h2 className="editorial-title console-side-title">Company Ledger</h2>
          <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
            Cash, invoices, liabilities, and current company run.
          </p>
        </div>
        <span className="ghost-pill">Run #{economics?.current_run_id ?? 1}</span>
      </div>

      <div
        className="console-inset"
        style={{ padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
      >
        {/* Revenue section */}
        <LedgerRow label="Cash In" value={economics?.revenue_eur} kind="positive" />
        <LedgerRow label="Invoiced Revenue" value={economics?.invoiced_revenue_eur} kind="positive" />
        <LedgerRow label="Accounts Receivable" value={economics?.accounts_receivable_eur} kind="positive" />
        <LedgerRow label="Accounts Payable" value={economics?.accounts_payable_eur} kind="cost" />

        {/* Divider */}
        <div
          style={{
            height: '1px',
            background: 'var(--border-subtle)',
            margin: '0.25rem 0',
          }}
          role="separator"
        />

        {/* Cost section */}
        <LedgerRow label="Operating Cost" value={economics?.operating_cost_eur} kind="cost" />
        <LedgerRow label="Pickup & Exchange Cost" value={economics?.rental_cost_eur} kind="cost" />
        <LedgerRow label="Overhead Cost" value={economics?.overhead_cost_eur} kind="cost" />
        <LedgerRow label="Penalty Cost" value={economics?.penalty_cost_eur} kind="cost" />
        <LedgerRow label="Penalty Avoided" value={economics?.overflow_penalty_avoided_eur} kind="positive" />
        <LedgerRow label="Early Empty Cost" value={economics?.early_empty_cost_eur} kind="cost" />

        {/* Divider */}
        <div
          style={{
            height: '1px',
            background: 'var(--border-subtle)',
            margin: '0.25rem 0',
          }}
          role="separator"
        />

        {/* Summary */}
        <LedgerRow label="Cash Balance" value={economics?.cash_balance_eur} kind="balance" large />
        <LedgerRow label="Realized Profit" value={economics?.profit_eur} kind="balance" large />
      </div>
    </section>
  );
}
