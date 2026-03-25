from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from raccoon_guardian.api.dependencies import AppContainer, get_container
from raccoon_guardian.api.schemas import (
    HealthResponse,
    MockEventRequest,
    RecommendationResponse,
    StrategySelectionRequest,
    TestActuationRequest,
)
from raccoon_guardian.domain.models import NotificationResult

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(container: AppContainer = Depends(get_container)) -> HealthResponse:
    return HealthResponse(status="ok", state=container.controller.state.value)


@router.get("/config")
def get_config(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    return container.config.model_dump(mode="json")


@router.post("/arm")
def arm(container: AppContainer = Depends(get_container)) -> dict[str, str]:
    return container.controller.arm()


@router.post("/disarm")
def disarm(container: AppContainer = Depends(get_container)) -> dict[str, str]:
    return container.controller.disarm()


@router.post("/events/mock")
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


@router.post("/strategies/select")
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


@router.post("/summary/morning/deliver", response_model=NotificationResult)
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


@router.post("/alerts/escalate", response_model=NotificationResult)
def escalate_failed_deterrence(
    container: AppContainer = Depends(get_container),
) -> NotificationResult:
    return container.tools.maybe_escalate_failed_deterrence()


@router.post("/actuate/test")
def test_actuation(
    payload: TestActuationRequest,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    if not container.config.safety.allow_test_actuation:
        raise HTTPException(status_code=403, detail="test actuation is disabled in config")
    record = container.controller.run_test_actuation(payload.strategy_name, payload.zone_id)
    return record.model_dump(mode="json")
