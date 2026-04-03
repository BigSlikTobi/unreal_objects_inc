import type { BaselineEconomicsDTO, ProjectedActionEconomicsDTO } from '../types';

interface Props {
  baseline: BaselineEconomicsDTO | null;
  projected?: ProjectedActionEconomicsDTO | null;
  compact?: boolean;
}

function money(value: number | null | undefined): string {
  return value == null ? '—' : `€${value.toFixed(0)}`;
}

function pct(value: number | null | undefined): string {
  return value == null ? '—' : `${(value * 100).toFixed(1)}%`;
}

function tone(value: number | null | undefined): string {
  if (value == null) return 'text-[var(--text-primary)]';
  if (value > 0) return 'text-[var(--tertiary)]';
  if (value < 0) return 'text-[var(--error)]';
  return 'text-[var(--amber)]';
}

export function OrderEconomicsPanel({ baseline, projected, compact = false }: Props) {
  if (!baseline) return null;

  return (
    <div className="console-inset px-3 py-3 text-[var(--text-secondary)]">
      <p className="section-label !mb-2">Order Economics</p>
      <div className={`grid gap-2 ${compact ? 'grid-cols-2' : 'grid-cols-2 lg:grid-cols-4'}`}>
        <div>
          <span className="section-label !mb-0">Baseline Margin</span>
          <div className={tone(baseline.baseline_margin_eur)}>{money(baseline.baseline_margin_eur)} / {pct(baseline.baseline_margin_pct)}</div>
        </div>
        <div>
          <span className="section-label !mb-0">Baseline Cost</span>
          <div className="text-[var(--text-primary)]">{money(baseline.baseline_total_cost_eur)}</div>
        </div>
        <div>
          <span className="section-label !mb-0">Receivable Gap</span>
          <div className="text-[var(--text-primary)]">{baseline.baseline_cash_gap_hours}h</div>
        </div>
        <div>
          <span className="section-label !mb-0">Payable Delay</span>
          <div className="text-[var(--text-primary)]">{baseline.baseline_payable_delay_hours}h</div>
        </div>
      </div>

      {projected && (
        <div className="mt-3 border-t border-[rgba(176,186,208,0.16)] pt-3">
          <p className="section-label !mb-2">Projected Chosen Action</p>
          <div className={`grid gap-2 ${compact ? 'grid-cols-2' : 'grid-cols-2 lg:grid-cols-4'}`}>
            <div>
              <span className="section-label !mb-0">Projected Margin</span>
              <div className={tone(projected.projected_margin_eur)}>{money(projected.projected_margin_eur)} / {pct(projected.projected_margin_pct)}</div>
            </div>
            <div>
              <span className="section-label !mb-0">Action Cost</span>
              <div className="text-[var(--text-primary)]">{money(projected.projected_action_cost_eur)}</div>
            </div>
            <div>
              <span className="section-label !mb-0">Projected Total</span>
              <div className="text-[var(--text-primary)]">{money(projected.projected_total_cost_eur)}</div>
            </div>
            <div>
              <span className="section-label !mb-0">Projected NWC</span>
              <div className={tone(projected.projected_net_working_capital_eur)}>{money(projected.projected_net_working_capital_eur)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
