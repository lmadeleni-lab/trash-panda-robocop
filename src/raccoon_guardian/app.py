from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

from raccoon_guardian.actuators.mock_actuators import MockActuatorHub
from raccoon_guardian.api.dependencies import AppContainer
from raccoon_guardian.api.routes import router
from raccoon_guardian.config import AppConfig, load_config
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.logging import configure_logging
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator
from raccoon_guardian.tools.bounded_actions import BoundedStrategyTools


def create_app(config: AppConfig | None = None, config_path: str | None = None) -> FastAPI:
    app_config = config or load_config(config_path or os.getenv("RG_CONFIG_PATH"))
    configure_logging(os.getenv("RG_LOG_LEVEL", app_config.logging.level))

    repository = EventRepository(app_config.database_path)
    strategy_catalog = StrategyCatalog()
    evaluator = StrategyEvaluator()
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
    )

    app = FastAPI(title="raccoon-guardian", version="0.1.0")
    app.state.container = AppContainer(
        config=app_config,
        controller=controller,
        repository=repository,
        strategy_catalog=strategy_catalog,
        evaluator=evaluator,
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
