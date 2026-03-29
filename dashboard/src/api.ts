import type {
  ApprovalItemDTO,
  ApprovalsResponse,
  ClockInfo,
  CompanyStatus,
  ContainersResponse,
  EconomicsSnapshot,
  OrdersResponse,
  PricingCatalogResponse,
  RulesResponse,
} from './types';

const BASE = import.meta.env.VITE_API_BASE || '/api/v1';

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store', ...init });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function operatorHeaders(operatorToken?: string): HeadersInit | undefined {
  return operatorToken ? { 'X-Operator-Token': operatorToken } : undefined;
}

export const fetchStatus = () => fetchJSON<CompanyStatus>('/status');
export const fetchClock = () => fetchJSON<ClockInfo>('/clock');
export const fetchOrders = () => fetchJSON<OrdersResponse>('/dashboard/orders');
export const fetchContainers = () => fetchJSON<ContainersResponse>('/containers');
export const fetchEconomics = () => fetchJSON<EconomicsSnapshot>('/economics');
export const fetchPricing = () => fetchJSON<PricingCatalogResponse>('/pricing');
export const fetchRules = () => fetchJSON<RulesResponse>('/rules');
export const fetchApprovals = () => fetchJSON<ApprovalsResponse>('/approvals');

export async function voteOnApproval(requestId: string, approved: boolean): Promise<ApprovalItemDTO> {
  return fetchJSON<ApprovalItemDTO>(`/approvals/${requestId}/vote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved }),
  });
}

export async function finalizeApproval(
  requestId: string,
  payload: { approved: boolean; reviewer: string; rationale?: string | null },
  operatorToken?: string,
): Promise<{ request_id: string; order_id: string; status: string; final_state: string }> {
  return fetchJSON(`/approvals/${requestId}/finalize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...operatorHeaders(operatorToken),
    },
    body: JSON.stringify(payload),
  });
}
