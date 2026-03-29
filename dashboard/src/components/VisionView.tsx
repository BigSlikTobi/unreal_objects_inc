export function VisionView() {
  return (
    <div className="console-view-stack">
      <section className="console-card p-5">
        <div className="console-panel-header">
          <div>
            <p className="console-panel-kicker">Vision</p>
            <h2 className="console-side-title editorial-title text-[var(--text-primary)]">What This Experiment Tries To Prove</h2>
          </div>
        </div>
        <div className="console-inset mt-4 space-y-4 p-5 text-sm leading-7 text-[var(--text-secondary)]">
          <p>
            `unreal_objects_inc` is a waste-management company simulation built to study autonomous agents under explicit guardrails.
            We are already convinced that a bot can make autonomous decisions. The real research question is different: how must
            guardrails be structured so an agent can stay fully autonomous without collapsing into overengineered prompts, hidden recipes,
            or manual steering?
          </p>
          <p>
            This test is explicitly about Unreal Objects as a secure guardrail layer for autonomous agents. The bot receives real-looking
            work, chooses its own action, and only then uses Unreal Objects to constrain that action. The goal is autonomy with guardrails,
            not autonomy with recipes. The guardrail system itself lives in{' '}
            <a
              href="https://github.com/BigSlikTobi/unreal_objects"
              target="_blank"
              rel="noreferrer"
              className="text-[var(--blue)] underline decoration-[rgba(130,170,249,0.45)] underline-offset-4 transition hover:text-white"
            >
              the Unreal Objects GitHub repository
            </a>
            .
          </p>
          <p>
            The company is intentionally economic. Containers have rental costs. Early emptying costs money. Overflow creates penalties.
            Bankruptcy forces a restart. But the company is no longer modeled as instant profit. Completed work becomes receivables first,
            cash arrives later, operating costs and overhead burn down liquidity over time, and bankruptcy is driven by cash stress rather
            than a simplistic revenue counter. This lets us observe whether the guardrail structure supports real commercial autonomy instead
            of forcing the agent into brittle scripted behavior.
          </p>
        </div>
      </section>

      <div className="console-dual-grid">
        <section className="console-card p-5">
          <div className="console-panel-header">
            <div>
              <p className="console-panel-kicker">Frame Conditions</p>
              <h2 className="console-side-title editorial-title text-[var(--text-primary)]">Operating Constraints</h2>
            </div>
          </div>
          <div className="console-inset mt-4 space-y-3 p-4 text-sm text-[var(--text-secondary)]">
            <p>The bot is external to the company.</p>
            <p>The bot decides first and asks Unreal Objects second.</p>
            <p>Rules constrain actions, not raw orders.</p>
            <p>Human steering and prompt scaffolding are intentionally minimized.</p>
            <p>Cashflow, overflow, and bankruptcy are first-class outcomes.</p>
          </div>
        </section>

        <section className="console-card p-5">
          <div className="console-panel-header">
            <div>
              <p className="console-panel-kicker">Proof Standard</p>
              <h2 className="console-side-title editorial-title text-[var(--text-primary)]">What Success Looks Like</h2>
            </div>
          </div>
          <div className="console-inset mt-4 space-y-3 p-4 text-sm text-[var(--text-secondary)]">
            <p>The bot stays autonomous while still operating safely.</p>
            <p>Guardrails block dangerous or loss-making actions without scripting the plan.</p>
            <p>Profitable orders are accepted intelligently without faking instant profit.</p>
            <p>Liquidity stays healthy while rent, overhead, and payment delay are respected.</p>
            <p>Overflow and bankruptcy stay lower than with weaker guardrails.</p>
            <p>Decision summaries make the bot’s reasoning inspectable after the fact.</p>
          </div>
        </section>
      </div>
    </div>
  );
}
