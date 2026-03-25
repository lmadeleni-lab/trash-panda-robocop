from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI

from raccoon_guardian.actuators.mock_actuators import MockActuatorHub
from raccoon_guardian.api.dependencies import AppContainer
from raccoon_guardian.api.routes import router
from raccoon_guardian.config import AppConfig, load_config
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.control.scheduler import RuntimeScheduler
from raccoon_guardian.logging import configure_logging, get_logger
from raccoon_guardian.notifications.slack import SlackNotifier
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator
from raccoon_guardian.tools.bounded_actions import BoundedStrategyTools

logger = get_logger(__name__)


async def runtime_scheduler_loop(app: FastAPI) -> None:
    container = app.state.container
    poll_interval_s = container.config.runtime.scheduler_poll_interval_s
    logger.info(
        "runtime scheduler started",
        extra={"context": {"poll_interval_s": poll_interval_s}},
    )
    while True:
        now = datetime.now(UTC)
        try:
            if (
                container.config.notifications.deliver_morning_summary
                and container.scheduler.should_deliver_morning_summary(now)
            ):
                target_date = container.scheduler.morning_summary_target_date(now)
                result = container.tools.deliver_morning_summary(target_date)
                logger.info(
                    "morning summary attempt completed",
                    extra={
                        "context": {
                            "date": target_date,
                            "delivered": result.delivered,
                            "detail": result.detail,
                        }
                    },
                )

            if container.scheduler.should_run_guard_round(now):
                results = container.tools.run_guard_round()
                logger.info(
                    "guard round completed",
                    extra={"context": {"actions_issued": len(results)}},
                )
        except Exception:
            logger.exception("runtime scheduler tick failed")
        await asyncio.sleep(poll_interval_s)


def create_app(config: AppConfig | None = None, config_path: str | None = None) -> FastAPI:
    app_config = config or load_config(config_path or os.getenv("RG_CONFIG_PATH"))
    configure_logging(os.getenv("RG_LOG_LEVEL", app_config.logging.level))

    repository = EventRepository(app_config.database_path)
    strategy_catalog = StrategyCatalog()
    evaluator = StrategyEvaluator()
    slack_notifier = SlackNotifier(
        webhook_url=app_config.notifications.slack_webhook_url,
        enabled=app_config.notifications.slack_enabled,
    )
    scheduler = RuntimeScheduler(
        timezone_name=app_config.safety.timezone,
        morning_summary=app_config.morning_summary,
        guard_rounds=app_config.guard_rounds,
        safety=app_config.safety,
    )
    controller = Controller(
        config=app_config,
        repository=repository,
        actuator_hub=MockActuatorHub(),
        strategy_catalog=strategy_catalog,
    )
    tools = BoundedStrategyTools(
        controller=controller,
        repository=repository,
        strategy_catalog=strategy_catalog,
        evaluator=evaluator,
        timezone_name=app_config.safety.timezone,
        slack_notifier=slack_notifier,
        escalation_failure_threshold=app_config.notifications.escalation_failure_threshold,
        scheduler=scheduler,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        task: asyncio.Task[None] | None = None
        if app_config.runtime.background_scheduler_enabled:
            task = asyncio.create_task(runtime_scheduler_loop(app))
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="raccoon-guardian", version="0.1.0", lifespan=lifespan)
    app.state.container = AppContainer(
        config=app_config,
        controller=controller,
        repository=repository,
        strategy_catalog=strategy_catalog,
        evaluator=evaluator,
        scheduler=scheduler,
        slack_notifier=slack_notifier,
        tools=tools,
    )
    app.include_router(router)
    return app


def main() -> None:
    host = os.getenv("RG_HOST", "127.0.0.1")
    port = int(os.getenv("RG_PORT", "8000"))
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
