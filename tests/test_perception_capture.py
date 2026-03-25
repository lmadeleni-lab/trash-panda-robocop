from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from raccoon_guardian.domain.enums import TargetClass
from raccoon_guardian.domain.models import NormalizedBBox
from raccoon_guardian.perception.base import DetectionCandidate, FramePacket
from raccoon_guardian.perception.capture import FrameSnapshotWriter
from raccoon_guardian.perception.realistic_detector import (
    ExternalModelDetector,
    FrameDifferenceDetector,
)


def test_frame_difference_detector_finds_motion() -> None:
    detector = FrameDifferenceDetector(min_area_px=200, confidence=0.7)
    baseline = np.zeros((160, 160, 3), dtype=np.uint8)
    moved = baseline.copy()
    moved[30:90, 40:100] = 255

    assert detector.detect(FramePacket(image=baseline, source="test")) == []
    detections = detector.detect(FramePacket(image=moved, source="test"))

    assert detections
    assert detections[0].confidence == 0.7


def test_external_model_detector_maps_predictions() -> None:
    class FakeBackend:
        def infer(self, frame: FramePacket) -> list[dict[str, object]]:
            del frame
            return [
                {
                    "label": "raccoon",
                    "confidence": 0.88,
                    "bbox": {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4},
                    "scores": {"raccoon": 0.88},
                    "backend": "fake_model",
                }
            ]

    detector = ExternalModelDetector(FakeBackend(), min_confidence=0.5)
    frame = FramePacket(image=np.zeros((32, 32, 3), dtype=np.uint8), source="fake")
    detections = detector.detect(frame)

    assert len(detections) == 1
    assert detections[0].target_class == TargetClass.RACCOON
    assert detections[0].metadata["backend"] == "fake_model"


def test_snapshot_writer_persists_image_and_metadata(tmp_path: Path) -> None:
    writer = FrameSnapshotWriter(tmp_path, max_saved_frames=5)
    frame = FramePacket(
        image=np.zeros((64, 64, 3), dtype=np.uint8),
        source="test",
        captured_at=datetime(2026, 1, 15, 2, 15, tzinfo=UTC),
        frame_id="frame-001",
    )
    path = writer.write(
        frame,
        label="unit",
        detections=[
            DetectionCandidate(
                target_class=TargetClass.RACCOON,
                confidence=0.82,
                bbox=NormalizedBBox(x1=0.1, y1=0.1, x2=0.4, y2=0.4),
            )
        ],
    )

    assert path.exists()
    assert path.with_suffix(".json").exists()
