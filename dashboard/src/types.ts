export interface CompanyStatus {
  virtual_time: string | null;
  current_run_started_at: string | null;
  acceleration: number | null;
  deployment_mode: string;
  public_voting_enabled: boolean;
  operator_auth_enabled: boolean;
  persistence_backend: string;
  bot_connected: boolean;
  bot_identity: string | null;
  bot_last_seen_at: string | null;
  current_run_id: number;
  stats: {
    total_orders: number;
    open_orders: number;
    claimed_orders: number;
    completed_orders: number;
    rejected_orders: number;
    blocked_orders: number;
    active_containers: number;
    rented_extra_containers: number;
    overflow_count: number;
    overflow_prevented_count: number;
    bankruptcy_count: number;
  };
}

export interface ClockInfo {
  virtual_time: string;
  acceleration: number;
  is_business_hours: boolean;
  activity_multiplier: number;
  day_of_week: string;
}

export interface DisposalOrderDTO {
  order_id: string;
  title: string;
  customer_request: string;
  declared_waste_type: string;
  quantity_m3: number;
  offered_price_eur: number;
  priority: string;
  service_window: string;
  created_at: string;
  customer_id: string | null;
  site_id: string | null;
  hazardous_flag: boolean;
  contamination_risk: boolean;
  status: string;
  assigned_to: string | null;
  baseline_economics: BaselineEconomicsDTO | null;
  projected_action_economics: ProjectedActionEconomicsDTO | null;
  action_inputs: Record<string, unknown>;
  guardrail_context_base: Record<string, unknown>;
  bot_action: string | null;
  action_payload: Record<string, unknown>;
  resolution: string | null;
  decision_outcome: string | null;
  decision_summary: string | null;
  request_id: string | null;
  matched_rules: string[];
  source_event_type: string | null;
  source_event_source: string | null;
  source_event_summary: string | null;
}

export interface OrdersResponse {
  orders: DisposalOrderDTO[];
  total: number;
}

export interface BotInboxOrderDTO {
  order_id: string;
  title: string;
  customer_request: string;
  declared_waste_type: string;
  quantity_m3: number;
  offered_price_eur: number;
  priority: string;
  service_window: string;
  created_at: string;
  customer_id: string | null;
  site_id: string | null;
  status: string;
  assigned_to: string | null;
  baseline_economics: BaselineEconomicsDTO | null;
  projected_action_economics: ProjectedActionEconomicsDTO | null;
  action_inputs: Record<string, unknown>;
  guardrail_context_base: Record<string, unknown>;
}

export interface BotOrdersResponse {
  orders: BotInboxOrderDTO[];
  total: number;
}

export interface ContainerDTO {
  container_id: string;
  label: string;
  waste_type: string;
  capacity_m3: number;
  fill_level_m3: number;
  fill_ratio: number;
  rental_cost_per_cycle_eur: number;
  base_early_empty_cost_eur: number;
  early_empty_cost_eur: number;
  emptying_interval_hours: number;
  hours_to_next_empty: number;
  next_empty_at: string;
  last_emptied_at: string;
  is_rented_extra: boolean;
  overflowed: boolean;
  overflow_penalty_eur: number;
  at_risk: boolean;
}

export interface ContainersResponse {
  containers: ContainerDTO[];
  total: number;
}

export interface EconomicsSnapshot {
  revenue_eur: number;
  invoiced_revenue_eur: number;
  operating_cost_eur: number;
  rental_cost_eur: number;
  overhead_cost_eur: number;
  penalty_cost_eur: number;
  early_empty_cost_eur: number;
  accounts_receivable_eur: number;
  accounts_payable_eur: number;
  cash_balance_eur: number;
  daily_burn_eur: number;
  bankruptcy_threshold_eur: number;
  runway_days: number;
  net_working_capital_eur: number;
  approval_locked_order_count: number;
  approval_locked_revenue_eur: number;
  profit_eur: number;
  overflow_count: number;
  overflow_prevented_count: number;
  overflow_penalty_avoided_eur: number;
  proactive_early_empty_cost_eur: number;
  bankruptcy_count: number;
  current_run_id: number;
}

export interface BaselineEconomicsDTO {
  customer_price_eur: number;
  baseline_service_cost_eur: number;
  baseline_total_cost_eur: number;
  baseline_margin_eur: number;
  baseline_margin_pct: number;
  baseline_receivable_delay_hours: number;
  baseline_payable_delay_hours: number;
  baseline_cash_gap_hours: number;
}

export interface ProjectedActionEconomicsDTO {
  projected_service_cost_eur: number;
  projected_action_cost_eur: number;
  projected_total_cost_eur: number;
  projected_margin_eur: number;
  projected_margin_pct: number;
  projected_receivable_delay_hours: number;
  projected_payable_delay_hours: number;
  projected_cash_gap_hours: number;
  projected_net_working_capital_eur: number;
  current_cash_balance_eur: number;
  current_accounts_receivable_eur: number;
  current_accounts_payable_eur: number;
  current_net_working_capital_eur: number;
  bankruptcy_threshold_eur: number;
  cost_policy_version: string;
}

export interface MarketPriceOptionDTO {
  option_id: string;
  waste_type: string;
  label: string;
  category: string;
  unit: string;
  base_price_eur: number;
  size_m3: number | null;
  price_per_m3_eur: number | null;
  price_per_kg_eur: number | null;
  notes: string | null;
  source_name: string;
  source_url: string;
  source_date: string | null;
}

export interface OperationalPriceOptionDTO {
  option_id: string;
  waste_type: string;
  bot_action: string;
  label: string;
  capacity_m3: number | null;
  rental_cost_per_cycle_eur: number | null;
  early_empty_cost_eur: number | null;
  turnaround_hours: number | null;
  notes: string | null;
  derived_from_source: string | null;
}

export interface PricingCatalogResponse {
  currency: string;
  market_quotes: MarketPriceOptionDTO[];
  operational_options: OperationalPriceOptionDTO[];
  policy: Record<string, unknown>;
}

export interface ApprovalVoteSummary {
  approve_votes: number;
  reject_votes: number;
  total_votes: number;
}

export interface ApprovalDecisionMetadata {
  approved: boolean;
  reviewer: string;
  rationale: string | null;
  decided_at: string;
}

export interface ApprovalItemDTO {
  request_id: string;
  order_id: string;
  title: string;
  customer_request: string;
  bot_action: string;
  baseline_economics: BaselineEconomicsDTO | null;
  projected_action_economics: ProjectedActionEconomicsDTO | null;
  decision_summary: string | null;
  matched_rules: string[];
  created_at: string;
  status: string;
  vote_summary: ApprovalVoteSummary;
  final_decision: ApprovalDecisionMetadata | null;
}

export interface ApprovalsResponse {
  approvals: ApprovalItemDTO[];
  total: number;
}

