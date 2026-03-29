import type { PricingCatalogResponse } from '../types';

interface Props {
  pricing: PricingCatalogResponse | null;
}

function money(value: number | null | undefined): string {
  if (value == null) return '—';
  return `€${value.toFixed(0)}`;
}

function titleCase(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase());
}

export function PricingPanel({ pricing }: Props) {
  const marketQuotes = pricing?.market_quotes.slice(0, 4) ?? [];
  const operationalOptions = pricing?.operational_options.slice(0, 4) ?? [];

  return (
    <section className="console-card console-side-panel p-5" aria-label="Pricing catalog">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Market & Ops Pricing</p>
          <h2 className="editorial-title console-side-title text-[var(--text-primary)]">Live Price Table</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Market anchors for customer pricing and internal action options for the bot.
          </p>
        </div>
        <span className="ghost-pill">{pricing?.currency ?? 'EUR'}</span>
      </div>

      <div className="console-inset mt-4 p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="section-label">Market Quotes</span>
          <span className="text-[11px] text-[var(--text-muted)]">{pricing?.market_quotes.length ?? 0} references</span>
        </div>
        <div className="space-y-2">
          {marketQuotes.length === 0 ? (
            <div className="text-sm italic text-[var(--text-secondary)]">No market pricing loaded.</div>
          ) : (
            marketQuotes.map((quote) => (
              <div key={quote.option_id} className="console-inset pricing-row px-3 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-[var(--text-primary)]">{quote.label}</div>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <span className="ghost-pill">{quote.waste_type}</span>
                      <span className="ghost-pill">{quote.unit}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-[var(--text-primary)]">{money(quote.base_price_eur)}</div>
                    <div className="text-[11px] text-[var(--text-secondary)]">
                      {quote.price_per_m3_eur != null
                        ? `${money(quote.price_per_m3_eur)}/m3`
                        : quote.price_per_kg_eur != null
                          ? `${quote.price_per_kg_eur.toFixed(2)} €/kg`
                          : quote.category}
                    </div>
                  </div>
                </div>
                <div className="mt-2 text-[11px] leading-5 text-[var(--text-secondary)]">
                  {quote.source_name}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="console-inset mt-4 p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="section-label">Action Options</span>
          <span className="text-[11px] text-[var(--text-muted)]">{pricing?.operational_options.length ?? 0} options</span>
        </div>
        <div className="space-y-2">
          {operationalOptions.length === 0 ? (
            <div className="text-sm italic text-[var(--text-secondary)]">No operational options loaded.</div>
          ) : (
            operationalOptions.map((option) => (
              <div key={option.option_id} className="console-inset pricing-row px-3 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-[var(--text-primary)]">{option.label}</div>
                    <div className="mt-1 flex flex-wrap gap-2">
                      <span className="ghost-pill">{option.waste_type}</span>
                      <span className="ghost-pill">{titleCase(option.bot_action)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-[var(--text-primary)]">
                      {money(option.rental_cost_per_cycle_eur ?? option.early_empty_cost_eur)}
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)]">
                      {option.capacity_m3 != null
                        ? `${option.capacity_m3.toFixed(0)} m3 · per exchange`
                        : option.turnaround_hours != null
                          ? `${option.turnaround_hours}h`
                          : 'option'}
                    </div>
                  </div>
                </div>
                <div className="mt-2 text-[11px] leading-5 text-[var(--text-secondary)]">
                  {option.notes ?? option.derived_from_source ?? ''}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
