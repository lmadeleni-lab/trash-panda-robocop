from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from raccoon_guardian.domain.models import DetectionEvent
from raccoon_guardian.perception.base import (
    DetectionCandidate,
    DetectionEventBuilder,
    Detector,
    FramePacket,
    FrameSource,
)
from raccoon_guardian.perception.capture import FrameSnapshotWriter


@dataclass(slots=True)
class PipelineResult:
    frame: FramePacket
    candidates: list[DetectionCandidate]
    events_count: int
    snapshot_path: Path | None


class PerceptionPipeline:
    def __init__(
        self,
        camera: FrameSource,
        detector: Detector,
        event_builder: DetectionEventBuilder,
        snapshot_writer: FrameSnapshotWriter | None = None,
    ) -> None:
        self.camera = camera
        self.detector = detector
        self.event_builder = event_builder
        self.snapshot_writer = snapshot_writer

    def process_next_frame(self) -> tuple[PipelineResult, list[DetectionEvent]]:
        frame = self.camera.capture_frame()
        candidates = self.detector.detect(frame)
        events = self.event_builder.build_events(frame, candidates)
        snapshot_path = None
        if self.snapshot_writer is not None:
            snapshot_path = self.snapshot_writer.write(
                frame,
                label="detections" if candidates else "frame",
                detections=candidates,
            )
        return (
            PipelineResult(
                frame=frame,
                candidates=candidates,
                events_count=len(events),
                snapshot_path=snapshot_path,
            ),
            events,
        )
