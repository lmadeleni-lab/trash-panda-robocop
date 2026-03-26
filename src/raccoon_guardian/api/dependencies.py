from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from raccoon_guardian.agents.service import MissionAgentOrchestrator
from raccoon_guardian.config import AppConfig
from raccoon_guardian.control.controller import Controller
from raccoon_guardian.control.scheduler import RuntimeScheduler
from raccoon_guardian.notifications.slack import SlackNotifier
from raccoon_guardian.storage.repository import EventRepository
from raccoon_guardian.strategies.catalog import StrategyCatalog
from raccoon_guardian.strategies.evaluator import StrategyEvaluator
from raccoon_guardian.tools.bounded_actions import BoundedStrategyTools


@dataclass(slots=True)
class AppContainer:
    config: AppConfig
    controller: Controller
    repository: EventRepository
    strategy_catalog: StrategyCatalog
    evaluator: StrategyEvaluator
    scheduler: RuntimeScheduler
    slack_notifier: SlackNotifier
    tools: BoundedStrategyTools
    mission_agents: MissionAgentOrchestrator


def get_container(request: Request) -> AppContainer:
    return request.app.state.container  # type: ignore[no-any-return]
