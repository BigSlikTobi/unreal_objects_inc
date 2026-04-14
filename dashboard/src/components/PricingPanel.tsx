import { useMemo, useState } from 'react';
import type { MarketPriceOptionDTO, OperationalPriceOptionDTO, PricingCatalogResponse } from '../types';

interface Props {
  pricing: PricingCatalogResponse | null;
}

function money(value: number | null | undefined): string {
  if (value == null) return '—';
  return `€${value.toFixed(0)}`;
}

function titleCase(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

function unitPrice(quote: MarketPriceOptionDTO): string {
  if (quote.price_per_m3_eur != null) return `${money(quote.price_per_m3_eur)}/m³`;
  if (quote.price_per_kg_eur != null) return `€${quote.price_per_kg_eur.toFixed(2)}/kg`;
  return quote.unit;
}

function optionCost(option: OperationalPriceOptionDTO): string {
  if (option.rental_cost_per_cycle_eur != null) return money(option.rental_cost_per_cycle_eur);
  if (option.early_empty_cost_eur != null) return money(option.early_empty_cost_eur);
  return '—';
}

function optionDetail(option: OperationalPriceOptionDTO): string {
  if (option.capacity_m3 != null) return `${option.capacity_m3.toFixed(0)} m³ per exchange`;
  if (option.turnaround_hours != null) return `${option.turnaround_hours}h turnaround`;
  return '';
}

/* ── Market quote card ── */
function QuoteCard({ quote }: { quote: MarketPriceOptionDTO }) {
  return (
    <div className="pricing-tile">
      <div className="pricing-tile-header">
        <span className="pricing-tile-price">{money(quote.base_price_eur)}</span>
        <span className="pricing-tile-unit">{unitPrice(quote)}</span>
      </div>
      <div className="pricing-tile-label">{quote.label}</div>
      <div className="pricing-tile-meta">
        <span>{quote.source_name}</span>
        {quote.notes && <span className="pricing-tile-note">{quote.notes}</span>}
      </div>
    </div>
  );
}

/* ── Operational option card ── */
function OptionCard({ option }: { option: OperationalPriceOptionDTO }) {
  return (
    <div className="pricing-tile pricing-tile-ops">
      <div className="pricing-tile-header">
        <span className="pricing-tile-price">{optionCost(option)}</span>
        <span className="pricing-tile-unit">{optionDetail(option)}</span>
      </div>
      <div className="pricing-tile-label">{option.label}</div>
      <div className="pricing-tile-meta">
        <span className="pricing-tile-action">{titleCase(option.bot_action)}</span>
        {(option.notes ?? option.derived_from_source) && (
          <span className="pricing-tile-note">{option.notes ?? option.derived_from_source}</span>
        )}
      </div>
    </div>
  );
}

function groupBy<T>(items: T[], key: (item: T) => string): [string, T[]][] {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const k = key(item);
    const group = map.get(k) ?? [];
    group.push(item);
    map.set(k, group);
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export function PricingPanel({ pricing }: Props) {
  const [wasteFilter, setWasteFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');

  /* Collect unique filter values */
  const allWasteTypes = useMemo(() => {
    const set = new Set<string>();
    for (const q of pricing?.market_quotes ?? []) set.add(q.waste_type);
    for (const o of pricing?.operational_options ?? []) set.add(o.waste_type);
    set.delete('all');
    return [...set].sort();
  }, [pricing]);

  const allCategories = useMemo(() => {
    const set = new Set<string>();
    for (const q of pricing?.market_quotes ?? []) set.add(q.category);
    set.delete('all');
    return [...set].sort();
  }, [pricing]);

  const allActions = useMemo(() => {
    const set = new Set<string>();
    for (const o of pricing?.operational_options ?? []) set.add(o.bot_action);
    set.delete('all');
    return [...set].sort();
  }, [pricing]);

  /* Filtered data */
  const filteredQuotes = useMemo(() => {
    return (pricing?.market_quotes ?? []).filter((q) => {
      if (wasteFilter !== 'all' && q.waste_type !== wasteFilter) return false;
      if (categoryFilter !== 'all' && q.category !== categoryFilter) return false;
      return true;
    });
  }, [pricing, wasteFilter, categoryFilter]);

  const filteredOps = useMemo(() => {
    return (pricing?.operational_options ?? []).filter((o) => {
      if (wasteFilter !== 'all' && o.waste_type !== wasteFilter) return false;
      if (actionFilter !== 'all' && o.bot_action !== actionFilter) return false;
      return true;
    });
  }, [pricing, wasteFilter, actionFilter]);

  const marketGroups = useMemo(() => groupBy(filteredQuotes, (q) => q.waste_type), [filteredQuotes]);
  const opsGroups = useMemo(() => groupBy(filteredOps, (o) => o.waste_type), [filteredOps]);

  const totalQuotes = pricing?.market_quotes.length ?? 0;
  const totalOps = pricing?.operational_options.length ?? 0;

  return (
    <section className="view-page flex min-h-0 flex-col" aria-label="Pricing catalog">
      {/* Header */}
      <div className="pricing-page-header">
        <div>
          <p className="console-panel-kicker">Market & Ops Pricing</p>
          <h2 className="console-panel-title">Live Price Table</h2>
        </div>
        <div className="console-panel-actions">
          <span className="ghost-pill">{pricing?.currency ?? 'EUR'}</span>
          <span className="ghost-pill">{totalQuotes + totalOps} references</span>
        </div>
      </div>

      {/* Filter bar */}
      <div className="pricing-filter-bar">
        {/* Waste type filter */}
        <div className="pricing-filter-group">
          <label className="pricing-filter-label">Waste Type</label>
          <div className="pricing-filter-chips">
            <button
              type="button"
              className={`order-filter-chip ${wasteFilter === 'all' ? 'order-filter-chip-active' : ''}`}
              onClick={() => setWasteFilter('all')}
            >
              All
            </button>
            {allWasteTypes.map((wt) => (
              <button
                key={wt}
                type="button"
                className={`order-filter-chip ${wasteFilter === wt ? 'order-filter-chip-active' : ''}`}
                onClick={() => setWasteFilter(wt)}
              >
                {wt}
              </button>
            ))}
          </div>
        </div>

        {/* Category filter (market quotes) */}
        {allCategories.length > 1 && (
          <div className="pricing-filter-group">
            <label className="pricing-filter-label">Category</label>
            <div className="pricing-filter-chips">
              <button
                type="button"
                className={`order-filter-chip ${categoryFilter === 'all' ? 'order-filter-chip-active' : ''}`}
                onClick={() => setCategoryFilter('all')}
              >
                All
              </button>
              {allCategories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`order-filter-chip ${categoryFilter === cat ? 'order-filter-chip-active' : ''}`}
                  onClick={() => setCategoryFilter(cat)}
                >
                  {titleCase(cat)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Action filter (operational options) */}
        {allActions.length > 1 && (
          <div className="pricing-filter-group">
            <label className="pricing-filter-label">Action</label>
            <div className="pricing-filter-chips">
              <button
                type="button"
                className={`order-filter-chip ${actionFilter === 'all' ? 'order-filter-chip-active' : ''}`}
                onClick={() => setActionFilter('all')}
              >
                All
              </button>
              {allActions.map((act) => (
                <button
                  key={act}
                  type="button"
                  className={`order-filter-chip ${actionFilter === act ? 'order-filter-chip-active' : ''}`}
                  onClick={() => setActionFilter(act)}
                >
                  {titleCase(act)}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="view-data-card pricing-sections">
        {/* ── Market Quotes ── */}
        <div className="pricing-section">
          <div className="pricing-section-header">
            <span className="pricing-section-title">Market Quotes</span>
            <span className="pricing-section-count">{filteredQuotes.length}{filteredQuotes.length !== totalQuotes ? ` / ${totalQuotes}` : ''}</span>
          </div>

          {marketGroups.length === 0 ? (
            <div className="pricing-empty">
              {totalQuotes === 0 ? 'No market pricing loaded.' : 'No quotes match the current filters.'}
            </div>
          ) : (
            <div className="pricing-type-yard">
              {marketGroups.map(([wasteType, quotes]) => (
                <div key={wasteType} className="pricing-type-group">
                  <div className="pricing-type-row">
                    <span className="pricing-type-label">{wasteType}</span>
                    <span className="pricing-type-count">{quotes.length}</span>
                  </div>
                  <div className="pricing-tile-grid">
                    {quotes.map((q) => (
                      <QuoteCard key={q.option_id} quote={q} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Action Options ── */}
        <div className="pricing-section">
          <div className="pricing-section-header">
            <span className="pricing-section-title">Action Options</span>
            <span className="pricing-section-count">{filteredOps.length}{filteredOps.length !== totalOps ? ` / ${totalOps}` : ''}</span>
          </div>

          {opsGroups.length === 0 ? (
            <div className="pricing-empty">
              {totalOps === 0 ? 'No operational options loaded.' : 'No options match the current filters.'}
            </div>
          ) : (
            <div className="pricing-type-yard">
              {opsGroups.map(([wasteType, options]) => (
                <div key={wasteType} className="pricing-type-group">
                  <div className="pricing-type-row">
                    <span className="pricing-type-label">{wasteType}</span>
                    <span className="pricing-type-count">{options.length}</span>
                  </div>
                  <div className="pricing-tile-grid">
                    {options.map((o) => (
                      <OptionCard key={o.option_id} option={o} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
