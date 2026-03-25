from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from raccoon_guardian.api.dependencies import AppContainer, get_container
from raccoon_guardian.api.schemas import (
    HealthResponse,
    MockEventRequest,
    StrategySelectionRequest,
    TestActuationRequest,
)

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


@router.post("/actuate/test")
def test_actuation(
    payload: TestActuationRequest,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    if not container.config.safety.allow_test_actuation:
        raise HTTPException(status_code=403, detail="test actuation is disabled in config")
    record = container.controller.run_test_actuation(payload.strategy_name, payload.zone_id)
    return record.model_dump(mode="json")
