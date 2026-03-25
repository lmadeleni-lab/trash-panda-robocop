from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from raccoon_guardian.api.dependencies import AppContainer, get_container
from raccoon_guardian.api.schemas import (
    HealthResponse,
    MockEventRequest,
    ReadinessResponse,
    RecommendationResponse,
    StrategySelectionRequest,
    TestActuationRequest,
)
from raccoon_guardian.api.security import require_control_access
from raccoon_guardian.domain.models import NotificationResult, SchedulerStatus, SystemStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(container: AppContainer = Depends(get_container)) -> HealthResponse:
    return HealthResponse(status="ok", state=container.controller.state.value)


@router.get("/health/ready", response_model=ReadinessResponse)
def ready(container: AppContainer = Depends(get_container)) -> ReadinessResponse:
    try:
        container.repository.list_encounters(limit=1)
        database_accessible = True
    except Exception:
        database_accessible = False
    checks = {
        "database_accessible": database_accessible,
        "strategies_loaded": bool(container.strategy_catalog.list_strategies()),
        "api_key_configured": (
            (not container.config.security.api_key_enabled)
            or bool(container.config.security.api_key)
        ),
        "slack_ready": (
            (not container.config.notifications.slack_enabled)
            or bool(container.config.notifications.slack_webhook_url)
        ),
    }
    status = "ready" if all(checks.values()) else "degraded"
    return ReadinessResponse(status=status, state=container.controller.state.value, checks=checks)


@router.get("/status", response_model=SystemStatus)
def status(container: AppContainer = Depends(get_container)) -> SystemStatus:
    return container.tools.system_status()


@router.get("/scheduler", response_model=SchedulerStatus)
def scheduler_status(container: AppContainer = Depends(get_container)) -> SchedulerStatus:
    return container.tools.scheduler_status()


@router.get("/config")
def get_config(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    return container.config.public_config()


@router.post("/arm", dependencies=[Depends(require_control_access)])
def arm(container: AppContainer = Depends(get_container)) -> dict[str, str]:
    return container.controller.arm()


@router.post("/disarm", dependencies=[Depends(require_control_access)])
def disarm(container: AppContainer = Depends(get_container)) -> dict[str, str]:
    return container.controller.disarm()


@router.post("/events/mock", dependencies=[Depends(require_control_access)])
def post_mock_event(
    payload: MockEventRequest,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    record = container.controller.process_detection(payload)
    return record.model_dump(mode="json")


@router.get("/events")
def list_events(
    limit: int = Query(default=100, ge=1, le=500),
    container: AppContainer = Depends(get_container),
) -> list[dict[str, object]]:
    return [
        record.model_dump(mode="json") for record in container.repository.list_encounters(limit)
    ]


@router.get("/strategies")
def list_strategies(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    return {
        "selected_strategy": container.controller.selected_strategy,
        "recommendations": {
            target_class.value: strategy_name.value
            for target_class, strategy_name in container.tools.recommendation_map().items()
        },
        "strategies": [
            strategy.model_dump(mode="json")
            for strategy in container.strategy_catalog.list_strategies()
        ],
    }


@router.post("/strategies/select", dependencies=[Depends(require_control_access)])
def select_strategy(
    payload: StrategySelectionRequest,
    container: AppContainer = Depends(get_container),
) -> dict[str, str]:
    strategy = container.controller.select_strategy(payload.strategy_name)
    return {"selected_strategy": strategy.value}


@router.get("/strategies/recommendations", response_model=list[RecommendationResponse])
def strategy_recommendations(
    container: AppContainer = Depends(get_container),
) -> list[RecommendationResponse]:
    return [
        RecommendationResponse(target_class=target_class, strategy_name=strategy_name)
        for target_class, strategy_name in container.tools.recommendation_map().items()
    ]


@router.get("/summary/nightly")
def nightly_summary(
    date: str | None = Query(default=None),
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    if date is None:
        current_date = datetime.now(container.config.safety.tzinfo).date().isoformat()
    else:
        current_date = date
    summary = container.tools.get_nightly_summary(current_date)
    return summary.model_dump(mode="json")


@router.post(
    "/summary/morning/deliver",
    response_model=NotificationResult,
    dependencies=[Depends(require_control_access)],
)
def deliver_morning_summary(
    date: str | None = Query(default=None),
    container: AppContainer = Depends(get_container),
) -> NotificationResult:
    if date is None:
        current_date = (
            datetime.now(container.config.safety.tzinfo).date() - timedelta(days=1)
        ).isoformat()
    else:
        current_date = date
    return container.tools.deliver_morning_summary(current_date)


@router.post(
    "/alerts/escalate",
    response_model=NotificationResult,
    dependencies=[Depends(require_control_access)],
)
def escalate_failed_deterrence(
    container: AppContainer = Depends(get_container),
) -> NotificationResult:
    return container.tools.maybe_escalate_failed_deterrence()


@router.post("/guard-rounds/run", dependencies=[Depends(require_control_access)])
def run_guard_round(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    try:
        results = container.tools.run_guard_round()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "count": len(results),
        "results": [result.model_dump(mode="json") for result in results],
    }


@router.post("/actuate/test", dependencies=[Depends(require_control_access)])
def test_actuation(
    payload: TestActuationRequest,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    if not container.config.safety.allow_test_actuation:
        raise HTTPException(status_code=403, detail="test actuation is disabled in config")
    record = container.controller.run_test_actuation(payload.strategy_name, payload.zone_id)
    return record.model_dump(mode="json")
