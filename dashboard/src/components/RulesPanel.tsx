import { useState } from 'react';
import { ChevronDown, ChevronRight, Shield } from 'lucide-react';
import type { RuleDTO, RuleGroupDTO } from '../types';

interface Props {
  rules: RuleDTO[];
  groups?: RuleGroupDTO[];
}

function RuleRow({ rule }: { rule: RuleDTO }) {
  const [expanded, setExpanded] = useState(false);
  const hasEdgeCases = rule.edge_cases.length > 0;

  return (
    <div className={`console-inset ${expanded ? 'relative z-10' : ''}`}>
      <div
        className={`flex items-start gap-3 px-4 py-4 ${hasEdgeCases ? 'cursor-pointer' : ''}`}
        onClick={() => hasEdgeCases && setExpanded(!expanded)}
        role={hasEdgeCases ? 'button' : undefined}
        tabIndex={hasEdgeCases ? 0 : undefined}
        onKeyDown={hasEdgeCases ? (e) => { if (e.key === 'Enter' || e.key === ' ') setExpanded(!expanded); } : undefined}
        aria-expanded={hasEdgeCases ? expanded : undefined}
      >
        {hasEdgeCases ? (
          expanded
            ? <ChevronDown className="w-4 h-4 text-[var(--text-secondary)] mt-0.5 shrink-0" />
            : <ChevronRight className="w-4 h-4 text-[var(--text-secondary)] mt-0.5 shrink-0" />
        ) : (
          <Shield className="mt-0.5 h-4 w-4 shrink-0 text-[var(--blue)]" />
        )}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--text-primary)]">{rule.name}</span>
            <span className="ghost-pill">{rule.feature}</span>
            {rule.group_name && <span className="ghost-pill">{rule.group_name}</span>}
          </div>
          <p className="text-xs text-[var(--text-secondary)] mt-1">{rule.rule_logic}</p>
        </div>
      </div>
      {expanded && hasEdgeCases && (
        <div className="px-4 pb-4 pt-1 pl-11">
          <div className="console-inset space-y-2 p-3">
            <p className="section-label">Edge Cases</p>
            {rule.edge_cases.map((ec, i) => (
              <p key={i} className="text-xs text-[var(--text-secondary)]">{ec}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function RulesPanel({ rules, groups = [] }: Props) {
  const activeRules = rules.filter((r) => r.active);
  const featuredRule = activeRules[0];

  return (
    <section className="console-card console-side-panel flex flex-col min-h-0 p-5" aria-label="Active rules">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Governance</p>
          <h2 className="editorial-title console-side-title text-[var(--text-primary)]">Active Rulebook</h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Live groups and rules mirrored from Unreal Objects.
          </p>
        </div>
        <span className="ghost-pill">{groups.length > 0 ? `${groups.length} groups` : `${activeRules.length} active`}</span>
      </div>

      {groups.length > 0 && (
        <div className="console-inset mb-4 grid gap-2 p-4 sm:grid-cols-2">
          {groups.map((group) => (
            <div key={group.id} className="rule-group-tile">
              <div className="section-label">{group.name}</div>
              <div className="mt-2 text-sm font-semibold text-[var(--text-primary)]">{group.rule_count} rules</div>
              <div className="mt-1 text-[11px] text-[var(--text-secondary)]">{group.id.slice(0, 8)}</div>
            </div>
          ))}
        </div>
      )}

      {featuredRule && (
        <div className="console-inset console-featured-rule mb-4 p-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="section-label">Active governance rule</span>
            <span className="status-chip status-neutral">stable</span>
          </div>
          <div className="text-sm font-semibold text-[var(--amber)]">{featuredRule.name}</div>
          <p className="console-featured-rule-copy mt-3 border-l border-[rgba(255,204,113,0.35)] pl-3 text-sm leading-6 text-[var(--text-secondary)]">
            “{featuredRule.rule_logic}”
          </p>
        </div>
      )}

      <div className="feed-scroll">
        <div className="feed-stack">
          {activeRules.length === 0 ? (
            <div className="console-inset px-4 py-8 text-sm italic text-[var(--text-secondary)]">No rules loaded</div>
          ) : (
            activeRules.slice(1, 8).map((r) => <RuleRow key={r.id} rule={r} />)
          )}
        </div>
      </div>
    </section>
  );
}
