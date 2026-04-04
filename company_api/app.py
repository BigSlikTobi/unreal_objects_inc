"""FastAPI app for the simulated waste-management company."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from support_company.models import DisposalOrder
from support_company.simulator import DEFAULT_LLM_MODEL

from .models import (
    ApprovalFinalizeRequest,
    ApprovalVoteRequest,
    ApprovalsResponse,
    BotInboxOrderDTO,
    BotOrdersResponse,
    DisposalOrderWebhookPayload,
    EventsResponse,
    OrderClaimRequest,
    OrderResultSubmission,
    OrdersResponse,
    PricingCatalogResponse,
)
from .service import CompanySimulationService
from .service import DEFAULT_ACCELERATION


def build_app(
    rule_pack_path: str | Path,
    initial_order_count: int | None = 24,
    rolling_generation: bool = False,
    seed: int = 42,
    acceleration: int = DEFAULT_ACCELERATION,
    generator_mode: str = "mixed",
    rule_engine_url: str = "http://127.0.0.1:8001",
    decision_center_url: str = "http://127.0.0.1:8002",
    rule_group_id: str | None = None,
    llm_model: str = DEFAULT_LLM_MODEL,
    llm_api_key: str | None = None,
    allow_template_fallback: bool = True,
    deployment_mode: str = "local",
    public_voting_enabled: bool | None = None,
    operator_auth_enabled: bool | None = None,
    operator_token: str | None = None,
    internal_api_key: str | None = None,
    persistence_path: str | Path | None = None,
    cost_policy_path: str | Path | None = None,
) -> FastAPI:
    service = CompanySimulationService(
        rule_pack_path=rule_pack_path,
        initial_order_count=initial_order_count,
        rolling_generation=rolling_generation,
        seed=seed,
        acceleration=acceleration,
        generator_mode=generator_mode,
        rule_engine_url=rule_engine_url,
        decision_center_url=decision_center_url,
        rule_group_id=rule_group_id,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        allow_template_fallback=allow_template_fallback,
        deployment_mode=deployment_mode,
        public_voting_enabled=public_voting_enabled,
        operator_auth_enabled=operator_auth_enabled,
        operator_token=operator_token,
        internal_api_key=internal_api_key,
        persistence_path=persistence_path,
        cost_policy_path=cost_policy_path,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await service.initialize()
        await service.start()
        app.state.company_service = service
        try:
            yield
        finally:
            await service.stop()

    app = FastAPI(title="Unreal Objects Inc Waste Company API", lifespan=lifespan)

    def require_operator(x_operator_token: str | None) -> None:
        if not service.operator_auth_enabled:
            return
        if not service.operator_token or x_operator_token != service.operator_token:
            raise HTTPException(status_code=401, detail="Invalid operator token")

    @app.get("/v1/health")
    async def health():
        return {"status": "ok", "service": "company_api"}

    @app.get("/api/v1/status")
    async def status():
        return await service.get_status()

    @app.get("/api/v1/clock")
    async def clock():
        return await service.get_clock()

    @app.get("/api/v1/orders", response_model=BotOrdersResponse)
    async def orders(status: str | None = None):
        current_orders = await service.get_bot_orders()
        if status is not None:
            current_orders = [order for order in current_orders if order.status == status]
        return BotOrdersResponse(orders=current_orders, total=len(current_orders))

    @app.get("/api/v1/dashboard/orders", response_model=OrdersResponse)
    async def dashboard_orders(status: str | None = None):
        current_orders = await service.get_orders()
        if status is not None:
            current_orders = [order for order in current_orders if order.status == status]
        return OrdersResponse(orders=current_orders, total=len(current_orders))

    @app.get("/api/v1/orders/{order_id}", response_model=BotInboxOrderDTO)
    async def get_order(order_id: str):
        try:
            return await service.get_bot_order(order_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Order not found") from exc

    @app.post("/api/v1/orders/{order_id}/claim")
    async def claim_order(order_id: str, payload: OrderClaimRequest):
        try:
            return await service.claim_order(order_id=order_id, bot_id=payload.bot_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Order not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/v1/orders/{order_id}/result")
    async def submit_order_result(order_id: str, payload: OrderResultSubmission):
        try:
            return await service.submit_order_result(
                order_id=order_id,
                bot_id=payload.bot_id,
                outcome=payload.outcome,
                bot_action=payload.bot_action,
                action_payload=payload.action_payload,
                decision_summary=payload.decision_summary,
                request_id=payload.request_id,
                matched_rules=payload.matched_rules,
                resolution=payload.resolution,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Order not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/v1/containers")
    async def containers():
        current_containers = await service.get_containers()
        return {"containers": current_containers, "total": len(current_containers)}

    @app.get("/api/v1/economics")
    async def economics():
        return await service.get_economics()

    @app.get("/api/v1/rules")
    async def rules():
        return await service.get_rules()

    @app.get("/api/v1/pricing", response_model=PricingCatalogResponse)
    async def pricing(waste_type: str | None = None):
        return await service.get_pricing(waste_type=waste_type)

    @app.get("/api/v1/events", response_model=EventsResponse)
    async def events():
        return await service.get_events()

    @app.get("/api/v1/approvals", response_model=ApprovalsResponse)
    async def approvals():
        current_approvals = await service.get_approvals()
        return ApprovalsResponse(approvals=current_approvals, total=len(current_approvals))

    @app.post("/api/v1/approvals/{request_id}/vote")
    async def vote_on_approval(request_id: str, payload: ApprovalVoteRequest):
        if not service.public_voting_enabled:
            raise HTTPException(status_code=404, detail="Public voting is disabled")
        try:
            return await service.record_public_vote(request_id=request_id, approved=payload.approved)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Approval request not found") from exc

    @app.post("/api/v1/approvals/{request_id}/finalize")
    async def finalize_approval(
        request_id: str,
        payload: ApprovalFinalizeRequest,
        x_operator_token: str | None = Header(default=None),
    ):
        require_operator(x_operator_token)
        try:
            return await service.finalize_approval(
                request_id=request_id,
                approved=payload.approved,
                reviewer=payload.reviewer,
                rationale=payload.rationale,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Approval request not found") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Failed to finalize approval with Unreal Objects: {exc}") from exc

    @app.post("/api/v1/webhooks/orders", response_model=OrdersResponse, status_code=202)
    async def orders_webhook(payload: DisposalOrderWebhookPayload):
        accepted = []
        for raw_order in payload.orders:
            order = DisposalOrder.model_validate(raw_order)
            accepted.append(await service.ingest_order(order))
        return OrdersResponse(orders=accepted, total=len(accepted))

    # Serve the dashboard static build if available
    # Check both the source-relative path (local dev) and /app (Docker container)
    dashboard_dist = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
    if not dashboard_dist.is_dir():
        dashboard_dist = Path("/app/dashboard/dist")
    if dashboard_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dashboard_dist / "assets"), name="dashboard-assets")

        @app.get("/{full_path:path}")
        async def serve_dashboard(full_path: str):
            """Catch-all: serve the SPA index.html for non-API routes."""
            file_path = dashboard_dist / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(dashboard_dist / "index.html")

    return app
