# Changelog — 2026-04-14

## Summary
Complete dashboard UI redesign aligning the `unreal_objects_inc` dashboard with the Unreal Objects admin panel style, introducing design tokens, light/dark theming, a collapsible sidebar, and fully rewritten page layouts for Orders, Containers, Pricing, Bot Activity, and Vision.

## Changes

### Layout & Navigation
- Sidebar is now always hidden behind a hamburger menu (consistent on all screen sizes); previous always-visible sidebar removed
- Theme toggle (night/dawn) moved from header into the sidebar
- Bankruptcy badge relocated from the Economics KPI card to the main header
- Performance and Systems pages removed; sidebar nav simplified to six core pages
- Page description lines removed from all views; `VIEW_META` description field dropped

### Design System
- Full CSS design token layer added to `index.css`: semantic color tokens for backgrounds, surfaces, text, borders, and brand accent across both `night` and `dawn` themes
- Light mode (dawn) contrast ratios improved throughout
- View page layout convention: headers and filter bars render on page background; data content sits on subtle card surfaces

### Orders Page
- Rewritten as a paginated table replacing the previous card/feed layout
- Status filter tabs added (All / Open / Claimed / Completed / etc.)
- Order detail modal popup added (`OrderDetailModal.tsx`) for full field inspection without leaving the page

### Containers Page
- Replaced flat list with visual container shapes showing fill levels
- Containers grouped by waste type in a responsive 2-column grid

### Pricing Page
- Rebuilt as a grouped tile layout
- Waste type, category, and action filters added
- 2-column grid separating market quotes from action options

### Bot Activity Page
- Clean structured layout with KPI strip, outcomes summary, live claims section, full history grid, and per-bot filter control

### Vision Page
- Typography cleaned up; full-width layout; blockquote styling applied

### Assets
- SVG logo (`unreal_objects.svg`) and favicon (`favicon.svg`) added to `dashboard/src/assets/`
- Favicon wired up in `index.html`

## Files Modified
- `dashboard/index.html` — favicon link updated
- `dashboard/src/DashboardApp.tsx` — sidebar redesign, hamburger menu, theme toggle moved, Performance/Systems pages removed, bankruptcy badge relocated, VIEW_META simplified
- `dashboard/src/index.css` — full design token system; light and dark theme variables; global layout and typography rules; major expansion (~+3200 lines net)
- `dashboard/src/main.tsx` — minor setup updates
- `dashboard/src/components/BotActivity.tsx` — full rewrite: KPI strip, outcomes, live claims, history grid, bot filter
- `dashboard/src/components/CaseCard.tsx` — updated to match new design tokens and card surface convention
- `dashboard/src/components/CaseFeed.tsx` — updated for paginated table layout
- `dashboard/src/components/ContainerFleet.tsx` — visual fill-level shapes, waste-type grouping
- `dashboard/src/components/DecisionOutcomes.tsx` — redesigned outcome summary tiles
- `dashboard/src/components/EconomicsPanel.tsx` — light mode contrast fixes, token adoption
- `dashboard/src/components/KpiStrip.tsx` — token-based styling, bankruptcy badge removed from card
- `dashboard/src/components/PerformanceView.tsx` — retained file but page removed from nav
- `dashboard/src/components/PricingPanel.tsx` — full rewrite: grouped tiles, filters
- `dashboard/src/components/VisionView.tsx` — typography and layout cleanup
- `dashboard/src/components/OrderDetailModal.tsx` — new file: order detail modal popup
- `dashboard/src/assets/favicon.svg` — new file
- `dashboard/src/assets/unreal_objects.svg` — new file
- `favicon.svg` — new file at repo root
- `unreal_objects.svg` — new file at repo root

## Code Quality Notes
- Python tests: 54 passed, 0 failed (0.56s)
- TypeScript type check (`tsc --noEmit`): passed with no errors
- ESLint: no `lint` script defined in dashboard `package.json`; no lint run possible. Pre-existing note: `AgentAdminPanel.tsx` and `ChatInterface.tsx` have known pre-existing ESLint issues (tracked separately; not introduced today)
- No `console.log`, `debugger`, TODO, FIXME, or HACK markers found in changed source files

## Open Items / Carry-over
- `PerformanceView.tsx` component file is still present on disk but the page is no longer reachable via nav — consider deleting the file in a follow-up cleanup
- `favicon.svg` and `unreal_objects.svg` appear at both the repo root and inside `dashboard/src/assets/` — verify the root copies are intentional or remove the duplicates
- No `lint` script in `dashboard/package.json` — consider adding ESLint config to enable automated lint checks in future day-closings
