export function VisionView() {
  return (
    <section className="view-page" aria-label="Vision">
      {/* Header */}
      <div className="vision-header">
        <p className="console-panel-kicker">Vision</p>
        <h2 className="console-panel-title">What This Experiment Tries To Prove</h2>
      </div>

      {/* Body */}
      <div className="view-data-card vision-body">
        {/* Main thesis */}
        <div className="vision-section">
          <p>
            <strong>unreal_objects_inc</strong> is a waste-management company simulation built to
            study autonomous agents under explicit guardrails. We are already convinced that a bot
            can make autonomous decisions. The real research question is different:
          </p>
          <blockquote className="vision-quote">
            How must guardrails be structured so an agent can stay fully autonomous without
            collapsing into overengineered prompts, hidden recipes, or manual steering?
          </blockquote>
          <p>
            This test is explicitly about{' '}
            <a
              href="https://github.com/BigSlikTobi/unreal_objects"
              target="_blank"
              rel="noreferrer"
              className="vision-link"
            >
              Unreal Objects
            </a>{' '}
            as a secure guardrail layer for autonomous agents. The bot receives real-looking work,
            chooses its own action, and only then uses Unreal Objects to constrain that action.
            The goal is autonomy with guardrails, not autonomy with recipes.
          </p>
          <p>
            The company is intentionally economic. Containers have rental costs. Early emptying
            costs money. Overflow creates penalties. Bankruptcy forces a restart. Completed work
            becomes receivables first, cash arrives later, operating costs and overhead burn down
            liquidity over time, and bankruptcy is driven by cash stress rather than a simplistic
            revenue counter. This lets us observe whether the guardrail structure supports real
            commercial autonomy instead of forcing the agent into brittle scripted behavior.
          </p>
        </div>

        {/* Two-column: constraints + success */}
        <div className="vision-grid">
          <div className="vision-card">
            <h3 className="vision-card-title">Operating Constraints</h3>
            <ul className="vision-list">
              <li>The bot is external to the company.</li>
              <li>The bot decides first and asks Unreal Objects second.</li>
              <li>Rules constrain actions, not raw orders.</li>
              <li>Human steering and prompt scaffolding are intentionally minimized.</li>
              <li>Cashflow, overflow, and bankruptcy are first-class outcomes.</li>
            </ul>
          </div>

          <div className="vision-card">
            <h3 className="vision-card-title">What Success Looks Like</h3>
            <ul className="vision-list">
              <li>The bot stays autonomous while still operating safely.</li>
              <li>Guardrails block dangerous or loss-making actions without scripting the plan.</li>
              <li>Profitable orders are accepted intelligently without faking instant profit.</li>
              <li>Liquidity stays healthy while rent, overhead, and payment delay are respected.</li>
              <li>Overflow and bankruptcy stay lower than with weaker guardrails.</li>
              <li>Decision summaries make the bot's reasoning inspectable after the fact.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
