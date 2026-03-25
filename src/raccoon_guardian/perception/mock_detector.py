from __future__ import annotations

from collections import deque

from raccoon_guardian.perception.base import DetectionCandidate, Detector, FramePacket


class MockDetector(Detector):
    def __init__(self, scripted_events: list[DetectionCandidate] | None = None) -> None:
        self._events = deque(scripted_events or [])

    def push(self, event: DetectionCandidate) -> None:
        self._events.append(event)

    def detect(self, frame: FramePacket) -> list[DetectionCandidate]:
        del frame
        if not self._events:
            return []
        return [self._events.popleft()]
