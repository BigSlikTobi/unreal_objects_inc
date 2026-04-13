import { useState } from 'react';
import type { ApprovalItemDTO, CompanyStatus } from '../types';
import { OrderEconomicsPanel } from './OrderEconomicsPanel';

const VOTE_COOLDOWN_MS = 5_000;

interface Props {
  approvals: ApprovalItemDTO[];
  status: CompanyStatus | null;
  onVote: (requestId: string, approved: boolean) => Promise<void>;
  onFinalize: (requestId: string, approved: boolean, reviewer: string, rationale?: string | null, operatorToken?: string) => Promise<void>;
  mode?: 'queue' | 'featured';
  onOpenAll?: () => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ApprovalQueue({ approvals, status, onVote, onFinalize, mode = 'queue', onOpenAll }: Props) {
  const [operatorToken, setOperatorToken] = useState(() => localStorage.getItem('uo_operator_token') ?? '');
  const [reviewer, setReviewer] = useState(() => localStorage.getItem('uo_operator_reviewer') ?? 'operator');
  const [finalizeBusyId, setFinalizeBusyId] = useState<string | null>(null);
  const [finalizeBusyAction, setFinalizeBusyAction] = useState<string | null>(null);
  const [optimisticVotes, setOptimisticVotes] = useState<Record<string, { approve: number; reject: number }>>({});
  const [voteCooldownUntil, setVoteCooldownUntil] = useState<Record<string, number>>({});
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isFeatured = mode === 'featured';
  const visibleApprovals = isFeatured
    ? [...approvals].sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime()).slice(0, 10)
    : approvals;

  function persistOperatorContext(nextToken: string, nextReviewer: string) {
    localStorage.setItem('uo_operator_token', nextToken);
    localStorage.setItem('uo_operator_reviewer', nextReviewer);
  }

  function voteLocked(requestId: string): boolean {
    return (voteCooldownUntil[requestId] ?? 0) > Date.now();
  }

  function displayedVoteSummary(approval: ApprovalItemDTO) {
    const optimistic = optimisticVotes[approval.request_id];
    const approveVotes = approval.vote_summary.approve_votes + (optimistic?.approve ?? 0);
    const rejectVotes = approval.vote_summary.reject_votes + (optimistic?.reject ?? 0);
    return {
      approveVotes,
      rejectVotes,
      totalVotes: approveVotes + rejectVotes,
    };
  }

  function resolveMatchedRules(ruleRefs: string[]): string[] {
    return ruleRefs;
  }

  const selectedApproval = selectedApprovalId ? visibleApprovals.find((approval) => approval.request_id === selectedApprovalId) ?? null : null;

  function renderApprovalDetails(approval: ApprovalItemDTO, detailMode: 'card' | 'modal') {
    const voteSummary = displayedVoteSummary(approval);
    const voteDisabled = voteLocked(approval.request_id);
    const matchedRuleNames = resolveMatchedRules(approval.matched_rules);
    const isModal = detailMode === 'modal';

    return (
      <>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="section-label !mb-1">{isModal ? 'Approval Required' : 'Pending Action'}</p>
            <div className={`${isModal ? 'text-lg' : 'text-sm'} font-medium text-[var(--text-primary)]`}>{approval.title}</div>
            <div className="mt-1 text-xs text-[var(--text-secondary)]">{approval.bot_action.replace(/_/g, ' ')}</div>
          </div>
          <span className="ghost-pill">{timeAgo(approval.created_at)}</span>
        </div>

        <p className={`${isModal ? 'approval-featured-request' : 'text-sm'} text-[var(--text-primary)]`}>"{approval.customer_request}"</p>
        <OrderEconomicsPanel
          baseline={approval.baseline_economics}
          projected={approval.projected_action_economics}
          compact={!isModal}
        />
        {approval.decision_summary && <p className={`${isModal ? 'text-sm leading-6' : 'text-xs'} text-[var(--text-secondary)]`}>{approval.decision_summary}</p>}

        {matchedRuleNames.length > 0 && (
          <div className="space-y-2">
            <p className="section-label !mb-0">Triggered Guardrails</p>
            <div className="feed-rule-row">
              {matchedRuleNames.map((rule) => (
                <span key={rule} className="feed-rule-pill">{rule}</span>
              ))}
            </div>
          </div>
        )}

        <div className="approval-vote-panel">
          <div className="approval-vote-header">
            <div>
              <p className="section-label !mb-0">Public Vote</p>
              <p className="approval-vote-cta">Should the company allow this action?</p>
            </div>
            <span className="ghost-pill">{voteSummary.totalVotes} total votes</span>
          </div>
          <div className="approval-vote-grid">
            <div className="approval-vote-stat approval-vote-stat-approve">
              <span className="section-label !mb-0">Approve</span>
              <strong>{voteSummary.approveVotes}</strong>
            </div>
            <div className="approval-vote-stat approval-vote-stat-reject">
              <span className="section-label !mb-0">Reject</span>
              <strong>{voteSummary.rejectVotes}</strong>
            </div>
          </div>
          {status?.public_voting_enabled && (
            <div className="approval-vote-actions">
              <button className="accent-button accent-button-approve" disabled={voteDisabled} onClick={() => handleVote(approval.request_id, true)}>
                {voteDisabled ? 'Vote Saved' : 'Vote Approve'}
              </button>
              <button className="accent-button accent-button-reject" disabled={voteDisabled} onClick={() => handleVote(approval.request_id, false)}>
                {voteDisabled ? 'Vote Saved' : 'Vote Reject'}
              </button>
            </div>
          )}
        </div>

        <div className="approval-final-actions">
          <p className="section-label !mb-0">Final Company Decision</p>
          <div className="flex flex-wrap gap-2">
            <button className="kinetic-button" disabled={finalizeBusyId === approval.request_id} onClick={() => handleFinalize(approval.request_id, true)}>
              {finalizeBusyId === approval.request_id && finalizeBusyAction === 'finalize-approve' ? 'Finalizing…' : 'Final approve'}
            </button>
            <button className="kinetic-button kinetic-button-muted" disabled={finalizeBusyId === approval.request_id} onClick={() => handleFinalize(approval.request_id, false)}>
              {finalizeBusyId === approval.request_id && finalizeBusyAction === 'finalize-reject' ? 'Rejecting…' : 'Final reject'}
            </button>
          </div>
        </div>
      </>
    );
  }

  function handleVote(requestId: string, approved: boolean) {
    if (voteLocked(requestId)) {
      setError('Please wait a few seconds before voting on the same approval again.');
      return;
    }

    setError(null);
    setOptimisticVotes((current) => ({
      ...current,
      [requestId]: {
        approve: (current[requestId]?.approve ?? 0) + (approved ? 1 : 0),
        reject: (current[requestId]?.reject ?? 0) + (approved ? 0 : 1),
      },
    }));
    setVoteCooldownUntil((current) => ({ ...current, [requestId]: Date.now() + VOTE_COOLDOWN_MS }));

    window.setTimeout(() => {
      setVoteCooldownUntil((current) => {
        const next = { ...current };
        if ((next[requestId] ?? 0) <= Date.now()) {
          delete next[requestId];
        }
        return next;
      });
      setOptimisticVotes((current) => {
        const next = { ...current };
        delete next[requestId];
        return next;
      });
    }, VOTE_COOLDOWN_MS);

    onVote(requestId, approved).catch((err) => {
      setOptimisticVotes((current) => {
        const next = { ...current };
        delete next[requestId];
        return next;
      });
      setError(err instanceof Error ? err.message : 'Vote failed');
    });
  }

  async function handleFinalize(requestId: string, approved: boolean) {
    setFinalizeBusyId(requestId);
    setFinalizeBusyAction(approved ? 'finalize-approve' : 'finalize-reject');
    setError(null);
    persistOperatorContext(operatorToken, reviewer);
    try {
      await onFinalize(requestId, approved, reviewer, null, operatorToken || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Finalize failed');
    } finally {
      setFinalizeBusyId(null);
      setFinalizeBusyAction(null);
    }
  }

  return (
    <section className={`console-card console-side-panel flex min-h-0 flex-col p-5 ${isFeatured ? 'approval-featured-panel' : ''}`} aria-label="Approval desk">
      <div className="console-panel-header console-side-header">
        <div>
          <p className="console-panel-kicker">Approvals</p>
          <h2 className={`editorial-title text-[var(--text-primary)] ${isFeatured ? 'approval-featured-title' : 'console-side-title'}`}>
            {isFeatured ? 'Oldest Approval Gallery' : 'Guardrail Escalations'}
          </h2>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            {isFeatured
              ? 'The oldest blocked actions waiting for a company decision.'
              : 'Pending `ASK_FOR_APPROVAL` decisions mirrored from Unreal Objects.'}
          </p>
        </div>
        {isFeatured ? (
          <button type="button" className="ghost-pill ghost-pill-button" onClick={onOpenAll} disabled={!onOpenAll}>
            {approvals.length} pending
          </button>
        ) : (
          <span className="ghost-pill">{approvals.length} pending</span>
        )}
      </div>

      {status?.operator_auth_enabled && (
        <div className="console-inset mt-4 grid gap-3 px-3 py-3 text-xs text-[var(--text-secondary)]">
          <label className="grid gap-1">
            <span className="section-label !mb-0">Reviewer</span>
            <input
              className="console-input"
              value={reviewer}
              onChange={(event) => setReviewer(event.target.value)}
              placeholder="operator"
            />
          </label>
          <label className="grid gap-1">
            <span className="section-label !mb-0">Operator Token</span>
            <input
              className="console-input"
              type="password"
              value={operatorToken}
              onChange={(event) => setOperatorToken(event.target.value)}
              placeholder="Required in hosted mode"
            />
          </label>
        </div>
      )}

      {error && <div className="console-inset mt-4 px-3 py-3 text-sm text-[var(--error)]">{error}</div>}

      {visibleApprovals.length === 0 ? (
        <div className="console-inset console-side-empty mt-4 flex flex-col items-center justify-center px-4 py-8 text-center text-[var(--text-secondary)]">
          <p className="text-sm italic">No approvals are waiting right now.</p>
        </div>
      ) : isFeatured ? (
        <div className="approval-featured-stack mt-4">
          <div className="approval-gallery-grid">
            {visibleApprovals.map((approval) => {
              const matchedRuleNames = resolveMatchedRules(approval.matched_rules);
              return (
                <button
                  key={approval.request_id}
                  type="button"
                  className="console-inset approval-gallery-card"
                  onClick={() => {
                    setSelectedApprovalId(approval.request_id);
                    setError(null);
                  }}
                >
                  <div className="approval-gallery-head">
                    <div>
                      <p className="section-label !mb-1">Approval Required</p>
                      <div className="text-sm font-medium text-[var(--text-primary)]">{approval.title}</div>
                    </div>
                    <span className="ghost-pill">{timeAgo(approval.created_at)}</span>
                  </div>
                  <p className="approval-gallery-request">"{approval.customer_request}"</p>
                  <div className="approval-gallery-rules">
                    <p className="section-label !mb-0">Guardrails</p>
                    <div className="feed-rule-row">
                      {matchedRuleNames.slice(0, 3).map((rule) => (
                        <span key={rule} className="feed-rule-pill">{rule}</span>
                      ))}
                      {matchedRuleNames.length > 3 && <span className="feed-rule-pill">+{matchedRuleNames.length - 3} more</span>}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {selectedApproval && (
            <div className="approval-modal-overlay" onClick={() => setSelectedApprovalId(null)}>
              <div className="console-card approval-modal" onClick={(event) => event.stopPropagation()}>
                <div className="console-panel-header approval-modal-header">
                  <div>
                    <p className="console-panel-kicker">Approval Required</p>
                    <h2 className="editorial-title approval-modal-title text-[var(--text-primary)]">{selectedApproval.title}</h2>
                    <p className="mt-2 text-sm text-[var(--text-secondary)]">
                      {selectedApproval.bot_action.replace(/_/g, ' ')} · {timeAgo(selectedApproval.created_at)}
                    </p>
                  </div>
                  <button type="button" className="ghost-pill ghost-pill-button" onClick={() => setSelectedApprovalId(null)}>
                    Close
                  </button>
                </div>

                <div className="approval-modal-body">
                  {renderApprovalDetails(selectedApproval, 'modal')}
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className={`console-side-list mt-4 ${isFeatured ? '' : 'space-y-3'}`}>
          {visibleApprovals.map((approval) => {
            return (
              <div key={approval.request_id} className={`console-inset space-y-3 px-3 py-3 ${isFeatured ? 'approval-featured-item' : ''}`}>
                {renderApprovalDetails(approval, 'card')}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
