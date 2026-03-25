from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from raccoon_guardian.perception.base import DetectionCandidate, FramePacket
from raccoon_guardian.perception.camera import cv2


class FrameSnapshotWriter:
    def __init__(self, capture_dir: Path, max_saved_frames: int = 250) -> None:
        self.capture_dir = capture_dir
        self.max_saved_frames = max_saved_frames
        self.capture_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        frame: FramePacket,
        *,
        label: str = "capture",
        detections: list[DetectionCandidate] | None = None,
    ) -> Path:
        if cv2 is None:
            msg = "opencv-python-headless is not installed"
            raise RuntimeError(msg)

        image = frame.image.copy()
        if detections:
            self._annotate(image, detections)

        output_path = (
            self.capture_dir
            / f"{frame.captured_at.strftime('%Y%m%d-%H%M%S')}-{label}-{frame.frame_id}.jpg"
        )
        ok = cv2.imwrite(str(output_path), image)
        if not ok:
            msg = f"failed to write frame snapshot to {output_path}"
            raise RuntimeError(msg)

        metadata_path = output_path.with_suffix(".json")
        metadata_path.write_text(
            json.dumps(
                {
                    "frame_id": frame.frame_id,
                    "source": frame.source,
                    "captured_at": frame.captured_at.isoformat(),
                    "detections": [
                        detection.model_dump(mode="json") for detection in detections or []
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self._prune_old_frames()
        return output_path

    def _annotate(self, image: Any, detections: list[DetectionCandidate]) -> None:
        if cv2 is None:
            return
        height, width = image.shape[:2]
        for detection in detections:
            x1 = int(detection.bbox.x1 * width)
            y1 = int(detection.bbox.y1 * height)
            x2 = int(detection.bbox.x2 * width)
            y2 = int(detection.bbox.y2 * height)
            label = f"{detection.target_class.value}:{detection.confidence:.2f}"
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 160), 2)
            cv2.putText(
                image,
                label,
                (x1, max(18, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

    def _prune_old_frames(self) -> None:
        jpg_files = sorted(self.capture_dir.glob("*.jpg"), key=lambda path: path.stat().st_mtime)
        if len(jpg_files) <= self.max_saved_frames:
            return
        for path in jpg_files[: len(jpg_files) - self.max_saved_frames]:
            metadata = path.with_suffix(".json")
            path.unlink(missing_ok=True)
            metadata.unlink(missing_ok=True)
