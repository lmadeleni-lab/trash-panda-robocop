from __future__ import annotations

from typing import Any, ClassVar, Protocol

from raccoon_guardian.domain.enums import TargetClass
from raccoon_guardian.domain.models import NormalizedBBox
from raccoon_guardian.perception.base import DetectionCandidate, Detector, FramePacket
from raccoon_guardian.perception.camera import cv2


class ModelBackend(Protocol):
    def infer(self, frame: FramePacket) -> list[dict[str, Any]]: ...


class FrameDifferenceDetector(Detector):
    """Deterministic motion detector for local development before ML integration."""

    def __init__(self, min_area_px: int = 900, confidence: float = 0.55) -> None:
        self.min_area_px = min_area_px
        self.confidence = confidence
        self._baseline_gray: Any | None = None

    def detect(self, frame: FramePacket) -> list[DetectionCandidate]:
        if cv2 is None:
            msg = "opencv-python-headless is not installed"
            raise RuntimeError(msg)

        gray = cv2.cvtColor(frame.image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (11, 11), 0)

        if self._baseline_gray is None:
            self._baseline_gray = gray
            return []

        delta = cv2.absdiff(self._baseline_gray, gray)
        _, threshold = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)
        threshold = cv2.dilate(threshold, None, iterations=2)
        contours, _hierarchy = cv2.findContours(
            threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        self._baseline_gray = gray

        height, width = gray.shape[:2]
        detections: list[DetectionCandidate] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area_px:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            bbox = NormalizedBBox(
                x1=x / width,
                y1=y / height,
                x2=(x + w) / width,
                y2=(y + h) / height,
            )
            detections.append(
                DetectionCandidate(
                    target_class=TargetClass.UNKNOWN,
                    confidence=self.confidence,
                    bbox=bbox,
                    scores={"motion": min(1.0, area / float(width * height))},
                    metadata={"backend": "frame_difference"},
                )
            )
        return detections


class ExternalModelDetector(Detector):
    """Adapter for future model runtimes such as ONNX, TFLite, or remote inference."""

    LABEL_MAP: ClassVar[dict[str, TargetClass]] = {
        "raccoon": TargetClass.RACCOON,
        "cat": TargetClass.CAT,
        "dog": TargetClass.DOG,
        "person": TargetClass.PERSON,
    }

    def __init__(self, backend: ModelBackend, min_confidence: float = 0.45) -> None:
        self.backend = backend
        self.min_confidence = min_confidence

    def detect(self, frame: FramePacket) -> list[DetectionCandidate]:
        detections: list[DetectionCandidate] = []
        for prediction in self.backend.infer(frame):
            confidence = float(prediction.get("confidence", 0.0))
            if confidence < self.min_confidence:
                continue
            label = str(prediction.get("label", "unknown")).lower()
            bbox_raw = prediction.get("bbox")
            if not isinstance(bbox_raw, dict):
                continue
            detections.append(
                DetectionCandidate(
                    target_class=self.LABEL_MAP.get(label, TargetClass.UNKNOWN),
                    confidence=confidence,
                    bbox=NormalizedBBox.model_validate(bbox_raw),
                    scores={
                        str(key): float(value)
                        for key, value in dict(prediction.get("scores", {})).items()
                    },
                    metadata={
                        "backend": str(prediction.get("backend", "external_model")),
                        "label": label,
                    },
                )
            )
        return detections
