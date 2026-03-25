from __future__ import annotations

from raccoon_guardian.control.controller import Controller
from raccoon_guardian.domain.models import DetectionEvent, EncounterRecord
from raccoon_guardian.strategies.evaluator import StrategyEvaluator


class NightSimulator:
    def __init__(self, controller: Controller, evaluator: StrategyEvaluator) -> None:
        self.controller = controller
        self.evaluator = evaluator

    def run(self, events: list[DetectionEvent]) -> list[EncounterRecord]:
        return [self.controller.process_detection(event) for event in events]
