import { CircleUserRound, Clock3, RadioTower, Settings2, Zap } from 'lucide-react';
import type { ClockInfo } from '../types';

export type TopSection = 'overview' | 'performance' | 'systems' | 'vision';

interface Props {
  clock: ClockInfo | null;
  connected: boolean;
  activeSection: TopSection;
  onSectionChange: (section: TopSection) => void;
}

function formatVirtualTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

const SECTIONS: { id: TopSection; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'performance', label: 'Performance' },
  { id: 'systems', label: 'Systems' },
  { id: 'vision', label: 'Vision' },
];

export function TopBar({ clock, connected, activeSection, onSectionChange }: Props) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-brand">
          <div className="topbar-title">Unreal Objects Inc.</div>
        </div>
        <nav className="topbar-nav" aria-label="View selector">
          {SECTIONS.map((section) => (
            <button
              key={section.id}
              type="button"
              className={`topbar-tab ${activeSection === section.id ? 'topbar-tab-active' : ''}`}
              onClick={() => onSectionChange(section.id)}
            >
              {section.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="topbar-status">
        <div className="topbar-indicator">
          <RadioTower className={`h-3.5 w-3.5 ${connected ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)]'}`} />
        </div>
        {clock && (
          <div className="topbar-chip">
            <Clock3 className="h-3.5 w-3.5" />
            <span>{formatVirtualTime(clock.virtual_time)}</span>
          </div>
        )}
        {clock && (
          <div className="topbar-chip">
            <Zap className="h-3.5 w-3.5" />
            <span>{clock.acceleration}x</span>
          </div>
        )}
        <div className="topbar-icon-button">
          <Settings2 className="h-4 w-4" />
        </div>
        <div className="topbar-icon-button topbar-icon-user">
          <CircleUserRound className="h-4 w-4" />
        </div>
      </div>
    </header>
  );
}
