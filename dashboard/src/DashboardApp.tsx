import { useCallback, useEffect, useState } from 'react';
import {
  BanknoteArrowDown,
  Bot,
  CircleHelp,
  Coins,
  LayoutDashboard,
  Menu,
  MoonStar,
  Recycle,
  RefreshCcw,
  SunMedium,
  TimerReset,
  X,
} from 'lucide-react';
import {
  fetchApprovals,
  fetchClock,
  fetchContainers,
  fetchEconomics,
  fetchOrders,
  fetchPricing,
  fetchStatus,
  finalizeApproval,
  voteOnApproval,
} from './api';
import { usePolling } from './hooks/usePolling';
import { ApprovalQueue } from './components/ApprovalQueue';
import { KpiStrip } from './components/KpiStrip';
import { CaseFeed } from './components/CaseFeed';
import { BotActivity } from './components/BotActivity';
import { DecisionOutcomes } from './components/DecisionOutcomes';
import { ContainerFleet } from './components/ContainerFleet';
import { EconomicsPanel } from './components/EconomicsPanel';
import { PricingPanel } from './components/PricingPanel';
import { VisionView } from './components/VisionView';

function formatCompanyAge(
  startedAt: string | null | undefined,
  virtualTime: string | null | undefined,
): string | null {
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
  | 'vision';

type DashboardTheme = 'night' | 'dawn';

const VIEW_TITLES: Record<DashboardView, string> = {
  overview: 'Overview',
  approvals: 'Approvals',
  orders: 'Orders',
  containers: 'Containers',
  pricing: 'Pricing',
  bot: 'Bot Activity',
  vision: 'Vision',
};

interface NavItem {
  view: DashboardView;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { view: 'overview', label: 'Overview', icon: <LayoutDashboard className="h-4 w-4" /> },
  { view: 'orders', label: 'Orders', icon: <BanknoteArrowDown className="h-4 w-4" /> },
  { view: 'containers', label: 'Containers', icon: <Recycle className="h-4 w-4" /> },
  { view: 'pricing', label: 'Pricing', icon: <Coins className="h-4 w-4" /> },
  { view: 'bot', label: 'Bot Activity', icon: <Bot className="h-4 w-4" /> },
  { view: 'vision', label: 'Vision', icon: <CircleHelp className="h-4 w-4" /> },
];

export function DashboardApp() {
  const [activeView, setActiveView] = useState<DashboardView>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<DashboardTheme>(() => {
    if (typeof window === 'undefined') return 'night';
    const stored = window.localStorage.getItem('uo_dashboard_theme');
    return stored === 'dawn' ? 'dawn' : 'night';
  });

  useEffect(() => {
    window.localStorage.setItem('uo_dashboard_theme', theme);
  }, [theme]);

  // Close sidebar on Escape key
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setSidebarOpen(false);
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const clockFetcher = useCallback(() => fetchClock(), []);
  const statusFetcher = useCallback(() => fetchStatus(), []);
  const ordersFetcher = useCallback(() => fetchOrders(), []);
  const containersFetcher = useCallback(() => fetchContainers(), []);
  const economicsFetcher = useCallback(() => fetchEconomics(), []);
  const pricingFetcher = useCallback(() => fetchPricing(), []);
  const approvalsFetcher = useCallback(() => fetchApprovals(), []);

  const clock = usePolling(clockFetcher, 2000);
  const status = usePolling(statusFetcher, 5000);
  const orders = usePolling(ordersFetcher, 5000);
  const containers = usePolling(containersFetcher, 5000);
  const economics = usePolling(economicsFetcher, 5000);
  const pricing = usePolling(pricingFetcher, 30000);
  const approvals = usePolling(approvalsFetcher, 5000);

  const apiHealthy = !clock.error && !status.error;
  const botConnected = status.data?.bot_connected ?? false;
  const allOrders = orders.data?.orders ?? [];
  const allContainers = containers.data?.containers ?? [];
  const allApprovals = approvals.data?.approvals ?? [];
  const currentTitle = VIEW_TITLES[activeView];
  const companyAge = formatCompanyAge(
    status.data?.current_run_started_at,
    status.data?.virtual_time,
  );
  const claimedOrders = status.data?.stats.claimed_orders ?? 0;

  function navigate(view: DashboardView) {
    setActiveView(view);
    setSidebarOpen(false);
  }

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
        </div>
      );
    }

    if (activeView === 'vision') {
      return <VisionView />;
    }

    // Overview
    return (
      <>
        <KpiStrip
          status={status.data}
          economics={economics.data}
          pricingReferenceCount={
            (pricing.data?.market_quotes.length ?? 0) +
            (pricing.data?.operational_options.length ?? 0)
          }
        />
        {claimedOrders > 0 && (
          <button
            type="button"
            className="overview-claim-indicator"
            onClick={() => navigate('bot')}
            aria-label={`${claimedOrders} orders currently claimed by bot. Open Bot Activity`}
          >
            <div className="overview-claim-indicator-dots" aria-hidden="true">
              {Array.from({ length: Math.min(claimedOrders, 10) }).map((_, index) => (
                <span key={index} className="pulse-dot pulse-dot-compact" />
              ))}
            </div>
            <div className="overview-claim-indicator-copy">
              <span className="section-label" style={{ marginBottom: 0 }}>
                Live Bot Claim
              </span>
              <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
                {status.data?.bot_identity ?? 'Bot'} claimed {claimedOrders} order
                {claimedOrders === 1 ? '' : 's'}
              </span>
            </div>
            <span className="ghost-pill ghost-pill-button">Open Bot Activity</span>
          </button>
        )}
        <div className="console-grid">
          <div className="console-column">
            <EconomicsPanel economics={economics.data} />
          </div>
          <div className="console-column">
            <DecisionOutcomes orders={allOrders} />
          </div>
        </div>
        <ApprovalQueue
          approvals={allApprovals}
          status={status.data}
          onVote={handleApprovalVote}
          onFinalize={handleApprovalFinalize}
          mode="featured"
          onOpenAll={() => navigate('approvals')}
        />
      </>
    );
  }

  return (
    <div className={`dashboard-shell ${theme === 'dawn' ? 'theme-dawn' : ''}`}>
      {/* Mobile sidebar backdrop */}
      <div
        className={`rail-backdrop ${sidebarOpen ? 'rail-open' : ''}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      <div className="dashboard-layout">
        {/* ── Sidebar ── */}
        <aside className={`command-rail ${sidebarOpen ? 'rail-open' : ''}`} aria-label="Main navigation">
          {/* Brand */}
          <div className="rail-brand">
            <img
              src={new URL('./assets/unreal_objects.svg', import.meta.url).href}
              alt="Unreal Objects"
              className="rail-brand-logo"
            />
            <div className="rail-brand-text">
              <span className="rail-brand-mark">Unreal Terminal</span>
              <span className="rail-brand-sub">waste ops</span>
            </div>
          </div>

          {/* Nav */}
          <div className="rail-body">
            <nav className="rail-nav" aria-label="Main navigation">
              {NAV_ITEMS.map(({ view, label, icon }) => (
                <button
                  key={view}
                  type="button"
                  className={`rail-link ${activeView === view ? 'rail-link-active' : ''}`}
                  onClick={() => navigate(view)}
                  aria-current={activeView === view ? 'page' : undefined}
                >
                  <span className="rail-link-icon" aria-hidden="true">{icon}</span>
                  <span className="rail-link-label">{label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Footer */}
          <div className="rail-footer">
            {/* Status badges */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <span
                className={`status-badge ${apiHealthy ? 'status-badge-green' : 'status-badge-red'}`}
                style={{ justifyContent: 'flex-start' }}
              >
                <span className="status-badge-dot" aria-hidden="true" />
                {apiHealthy ? 'API Online' : 'API Offline'}
              </span>
              <span
                className={`status-badge ${botConnected ? 'status-badge-green' : 'status-badge-neutral'}`}
                style={{ justifyContent: 'flex-start' }}
              >
                <span className="status-badge-dot" aria-hidden="true" />
                {botConnected ? 'Bot Connected' : 'Bot Offline'}
              </span>
            </div>

            {/* Theme toggle */}
            <button
              type="button"
              className="theme-toggle-button"
              onClick={() => setTheme((t) => (t === 'night' ? 'dawn' : 'night'))}
              aria-label={
                theme === 'night' ? 'Switch to light mode' : 'Switch to dark mode'
              }
            >
              {theme === 'night' ? (
                <SunMedium className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <MoonStar className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              <span>{theme === 'night' ? 'Light mode' : 'Dark mode'}</span>
            </button>

            <div className="operator-card">
              <div className="operator-avatar" aria-hidden="true">WM</div>
              <div className="operator-meta">
                <span className="operator-name">Waste Operations</span>
                <span className="operator-status">Autonomous</span>
              </div>
            </div>
          </div>
        </aside>

        {/* ── Main ── */}
        <main className="console-main" id="main-content">
          {/* Sticky header */}
          <header className="console-view-header">
            <div className="console-view-header-left">
              <button
                type="button"
                className="hamburger-button"
                onClick={() => setSidebarOpen((o) => !o)}
                aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}
                aria-expanded={sidebarOpen}
                aria-controls="main-content"
              >
                {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </button>

              <div className="console-view-header-title">
                <p className="console-panel-kicker">Workspace</p>
                <h1 className="console-panel-title">{currentTitle}</h1>
              </div>
            </div>

            <div className="console-panel-actions">
              {/* Company age */}
              {companyAge && (
                <span
                  className="run-age-pill"
                  title="Virtual age of the current company run"
                  aria-label={`Company age: ${companyAge}`}
                >
                  <TimerReset className="h-3.5 w-3.5" aria-hidden="true" />
                  <span className="run-age-label">Age</span>
                  <strong className="run-age-value">{companyAge}</strong>
                </span>
              )}

              {/* Bankruptcy count */}
              <span
                className={`ghost-pill ${(status.data?.stats.bankruptcy_count ?? 0) > 0 ? 'ghost-pill-danger' : ''}`}
                title={`Company run #${status.data?.current_run_id ?? 1}`}
                aria-label={`${status.data?.stats.bankruptcy_count ?? 0} bankruptcies, run #${status.data?.current_run_id ?? 1}`}
              >
                <RefreshCcw className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{status.data?.stats.bankruptcy_count ?? 0}</span>
              </span>

              {/* Clock info */}
              {clock.data && (
                <span className="ghost-pill" aria-label={`Speed: ${clock.data.acceleration}x`}>
                  {clock.data.acceleration}x
                </span>
              )}
              {clock.data && (
                <span className="ghost-pill">{clock.data.day_of_week}</span>
              )}
            </div>
          </header>

          {/* Content */}
          <div className="console-body">
            {/* Description under header */}
            {renderMainView()}
          </div>
        </main>
      </div>
    </div>
  );
}
