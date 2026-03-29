import { useCallback, useEffect, useState } from 'react';
import { BanknoteArrowDown, Bot, CircleHelp, Grid2x2, LayoutDashboard, MessagesSquare, MoonStar, Recycle, ShieldCheck, SunMedium, TimerReset } from 'lucide-react';
import { fetchApprovals, fetchClock, fetchContainers, fetchEconomics, fetchOrders, fetchPricing, fetchRules, fetchStatus, finalizeApproval, voteOnApproval } from './api';
import { usePolling } from './hooks/usePolling';
import { ApprovalQueue } from './components/ApprovalQueue';
import { KpiStrip } from './components/KpiStrip';
import { CaseFeed } from './components/CaseFeed';
import { BotActivity } from './components/BotActivity';
import { RulesPanel } from './components/RulesPanel';
import { DecisionOutcomes } from './components/DecisionOutcomes';
import { ContainerFleet } from './components/ContainerFleet';
import { EconomicsPanel } from './components/EconomicsPanel';
import { PricingPanel } from './components/PricingPanel';
import { PerformanceView } from './components/PerformanceView';
import { SystemsView } from './components/SystemsView';
import { VisionView } from './components/VisionView';

function formatCompanyAge(startedAt: string | null | undefined, virtualTime: string | null | undefined): string | null {
  if (!startedAt || !virtualTime) return null;
  const start = new Date(startedAt).getTime();
  const current = new Date(virtualTime).getTime();
  if (Number.isNaN(start) || Number.isNaN(current) || current < start) return null;

  const totalMinutes = Math.floor((current - start) / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const minutes = totalMinutes % 60;

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

type DashboardView =
  | 'overview'
  | 'approvals'
  | 'orders'
  | 'containers'
  | 'pricing'
  | 'bot'
  | 'guardrails'
  | 'performance'
  | 'systems'
  | 'vision';

type DashboardTheme = 'night' | 'dawn';

const VIEW_META: Record<DashboardView, { title: string; description: string }> = {
  overview: {
    title: 'Overview',
    description: 'Profit, bot posture, and company health at a glance.',
  },
  approvals: {
    title: 'Approvals',
    description: 'Every pending guardrail escalation that still needs a company decision.',
  },
  orders: {
    title: 'Orders',
    description: 'Live disposal intake and the current state of each customer order.',
  },
  containers: {
    title: 'Containers',
    description: 'Fleet capacity, fill levels, and operational pressure.',
  },
  pricing: {
    title: 'Pricing',
    description: 'Market-reference quotes and company action options for autonomous decisions.',
  },
  bot: {
    title: 'Bot Activity',
    description: 'How the external bot is engaging orders and how guardrails shape outcomes.',
  },
  guardrails: {
    title: 'Guardrails',
    description: 'Live groups and rules mirrored from Unreal Objects.',
  },
  performance: {
    title: 'Performance',
    description: 'Commercial quality, outcome mix, and current operational pressure.',
  },
  systems: {
    title: 'Systems',
    description: 'Runtime nodes, connectivity, and live company surfaces.',
  },
  vision: {
    title: 'Vision',
    description: 'Why this experiment exists and what it is trying to prove.',
  },
};

export function DashboardApp() {
  const [activeView, setActiveView] = useState<DashboardView>('overview');
  const [theme, setTheme] = useState<DashboardTheme>(() => {
    if (typeof window === 'undefined') {
      return 'night';
    }
    const stored = window.localStorage.getItem('uo_dashboard_theme');
    return stored === 'dawn' ? 'dawn' : 'night';
  });

  useEffect(() => {
    window.localStorage.setItem('uo_dashboard_theme', theme);
  }, [theme]);

  const clockFetcher = useCallback(() => fetchClock(), []);
  const statusFetcher = useCallback(() => fetchStatus(), []);
  const ordersFetcher = useCallback(() => fetchOrders(), []);
  const rulesFetcher = useCallback(() => fetchRules(), []);
  const containersFetcher = useCallback(() => fetchContainers(), []);
  const economicsFetcher = useCallback(() => fetchEconomics(), []);
  const pricingFetcher = useCallback(() => fetchPricing(), []);
  const approvalsFetcher = useCallback(() => fetchApprovals(), []);

  const clock = usePolling(clockFetcher, 2000);
  const status = usePolling(statusFetcher, 5000);
  const orders = usePolling(ordersFetcher, 5000);
  const rules = usePolling(rulesFetcher, 30000);
  const containers = usePolling(containersFetcher, 5000);
  const economics = usePolling(economicsFetcher, 5000);
  const pricing = usePolling(pricingFetcher, 30000);
  const approvals = usePolling(approvalsFetcher, 5000);

  const apiHealthy = !clock.error && !status.error;
  const botConnected = status.data?.bot_connected ?? false;
  const allOrders = orders.data?.orders ?? [];
  const allRules = rules.data?.rules ?? [];
  const allContainers = containers.data?.containers ?? [];
  const allApprovals = approvals.data?.approvals ?? [];
  const currentView = VIEW_META[activeView];
  const companyAge = formatCompanyAge(status.data?.current_run_started_at, status.data?.virtual_time);
  const claimedOrders = status.data?.stats.claimed_orders ?? 0;

  async function handleApprovalVote(requestId: string, approved: boolean) {
    await voteOnApproval(requestId, approved);
    approvals.refresh();
    orders.refresh();
    status.refresh();
  }

  async function handleApprovalFinalize(
    requestId: string,
    approved: boolean,
    reviewer: string,
    rationale?: string | null,
    operatorToken?: string,
  ) {
    await finalizeApproval(requestId, { approved, reviewer, rationale }, operatorToken);
    approvals.refresh();
    orders.refresh();
    economics.refresh();
    status.refresh();
  }

  function renderMainView() {
    if (activeView === 'orders') {
      return (
        <div className="console-view-stack">
          <CaseFeed orders={allOrders} />
        </div>
      );
    }

    if (activeView === 'approvals') {
      return (
        <div className="console-view-stack">
          <ApprovalQueue
            approvals={allApprovals}
            rules={allRules}
            status={status.data}
            onVote={handleApprovalVote}
            onFinalize={handleApprovalFinalize}
          />
        </div>
      );
    }

    if (activeView === 'containers') {
      return (
        <div className="console-view-stack">
          <ContainerFleet containers={allContainers} />
        </div>
      );
    }

    if (activeView === 'pricing') {
      return (
        <div className="console-view-stack">
          <PricingPanel pricing={pricing.data} />
        </div>
      );
    }

    if (activeView === 'bot') {
      return (
        <div className="console-view-stack">
          <BotActivity orders={allOrders} approvals={allApprovals} status={status.data} />
          <DecisionOutcomes orders={allOrders} />
        </div>
      );
    }

    if (activeView === 'guardrails') {
      return (
        <div className="console-view-stack">
          <RulesPanel rules={allRules} groups={rules.data?.groups ?? []} />
        </div>
      );
    }

    if (activeView === 'performance') {
      return <PerformanceView orders={allOrders} economics={economics.data} containers={allContainers} />;
    }

    if (activeView === 'systems') {
      return (
        <SystemsView
          apiHealthy={apiHealthy}
          botConnected={botConnected}
          status={status.data}
          rulesCount={allRules.length}
          pricing={pricing.data}
        />
      );
    }

    if (activeView === 'vision') {
      return <VisionView />;
    }

    return (
      <>
        <KpiStrip
          status={status.data}
          economics={economics.data}
          rulesCount={allRules.length}
          pricingReferenceCount={(pricing.data?.market_quotes.length ?? 0) + (pricing.data?.operational_options.length ?? 0)}
        />
        {claimedOrders > 0 && (
          <button type="button" className="overview-claim-indicator" onClick={() => setActiveView('bot')}>
            <div className="overview-claim-indicator-dots" aria-hidden="true">
              {Array.from({ length: Math.min(claimedOrders, 10) }).map((_, index) => (
                <span key={index} className="pulse-dot pulse-dot-compact" />
              ))}
            </div>
            <div className="overview-claim-indicator-copy">
              <span className="section-label !mb-0">Live Bot Claim</span>
              <span className="text-sm text-[var(--text-primary)]">
                {status.data?.bot_identity ?? 'Bot'} currently claimed {claimedOrders} order{claimedOrders === 1 ? '' : 's'}
              </span>
            </div>
            <span className="ghost-pill">Open Bot Activity</span>
          </button>
        )}
        <div className="console-grid">
          <div className="console-column min-h-0">
            <EconomicsPanel economics={economics.data} />
          </div>
          <div className="console-column min-h-0">
            <DecisionOutcomes orders={allOrders} />
          </div>
        </div>
        <ApprovalQueue
          approvals={allApprovals}
          rules={allRules}
          status={status.data}
          onVote={handleApprovalVote}
          onFinalize={handleApprovalFinalize}
          mode="featured"
          onOpenAll={() => setActiveView('approvals')}
        />
      </>
    );
  }

  return (
    <div className={`dashboard-shell ${theme === 'dawn' ? 'theme-dawn' : 'theme-night'}`}>
      <div className="dashboard-layout">
        <aside className="command-rail">
          <div className="rail-brand">
            <div className="rail-brand-emblem">
              <Grid2x2 className="h-4 w-4" />
            </div>
            <div className="rail-brand-mark">Unreal Terminal</div>
            <div className="rail-brand-sub">waste ops stable</div>
          </div>

          <div>
            <div className="rail-section-title">Operations</div>
            <nav className="rail-nav rail-nav-primary" aria-label="Operations">
              <button type="button" className={`rail-link ${activeView === 'overview' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('overview')}>
                <LayoutDashboard className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Overview</span></div>
              </button>
              <button type="button" className={`rail-link ${activeView === 'orders' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('orders')}>
                <BanknoteArrowDown className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Orders</span></div>
              </button>
              <button type="button" className={`rail-link ${activeView === 'containers' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('containers')}>
                <Recycle className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Containers</span></div>
              </button>
              <button type="button" className={`rail-link ${activeView === 'pricing' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('pricing')}>
                <BanknoteArrowDown className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Pricing</span></div>
              </button>
              <button type="button" className={`rail-link ${activeView === 'bot' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('bot')}>
                <Bot className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Bot Activity</span></div>
              </button>
              <button type="button" className={`rail-link ${activeView === 'guardrails' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('guardrails')}>
                <ShieldCheck className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Guardrails</span></div>
              </button>
            </nav>
          </div>

          <div>
            <div className="rail-section-title">Research</div>
            <nav className="rail-nav rail-nav-primary" aria-label="Research">
              <button type="button" className={`rail-link ${activeView === 'performance' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('performance')}>
                <LayoutDashboard className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Performance</span></div>
              </button>
              <button type="button" className={`rail-link ${activeView === 'systems' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('systems')}>
                <Grid2x2 className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Systems</span></div>
              </button>
              <button type="button" className={`rail-link ${activeView === 'vision' ? 'rail-link-active' : ''}`} onClick={() => setActiveView('vision')}>
                <CircleHelp className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy"><span className="rail-link-label">Vision</span></div>
              </button>
            </nav>
          </div>

          <div className="rail-footer">
            <nav className="rail-nav rail-nav-utility" aria-label="Utility">
              <div className="rail-link rail-link-utility">
                <MessagesSquare className="h-4 w-4 rail-link-icon" />
                <div className="rail-link-copy">
                  <span className="rail-link-label">Discord</span>
                  <span className="rail-link-meta">Coming soon</span>
                </div>
              </div>
            </nav>

            <div className="operator-card">
              <div className="operator-avatar">WM</div>
              <div className="operator-meta">
                <span className="operator-name">Waste Operations</span>
                <span className="operator-status">Autonomous</span>
              </div>
            </div>
          </div>
        </aside>

        <main className="console-main">
          <section className="console-view-header">
            <div>
              <p className="console-panel-kicker">Workspace</p>
              <h1 className="console-panel-title">{currentView.title}</h1>
              <p className="console-view-copy">{currentView.description}</p>
            </div>
            <div className="console-panel-actions">
              <button
                type="button"
                className="theme-toggle-button"
                onClick={() => setTheme((current) => (current === 'night' ? 'dawn' : 'night'))}
                title={theme === 'night' ? 'Switch to brighter mode' : 'Switch to darker mode'}
              >
                {theme === 'night' ? <SunMedium className="h-3.5 w-3.5" /> : <MoonStar className="h-3.5 w-3.5" />}
                <span>{theme === 'night' ? 'Bright mode' : 'Night mode'}</span>
              </button>
              {companyAge && (
                <span className="run-age-pill" title="Virtual age of the current company run">
                  <TimerReset className="h-3.5 w-3.5" />
                  <span className="run-age-label">Company Age</span>
                  <strong className="run-age-value">{companyAge}</strong>
                </span>
              )}
              <span className="ghost-pill">{apiHealthy ? 'API online' : 'API offline'}</span>
              <span className="ghost-pill">{botConnected ? 'Bot connected' : 'Bot offline'}</span>
              {clock.data && <span className="ghost-pill">{clock.data.acceleration}x</span>}
              {clock.data && <span className="ghost-pill">{clock.data.day_of_week}</span>}
            </div>
          </section>
          {renderMainView()}
        </main>
      </div>
    </div>
  );
}
