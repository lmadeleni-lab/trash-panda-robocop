from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any
from uuid import uuid4

from raccoon_guardian.perception.base import FramePacket

cv2: Any | None
if importlib.util.find_spec("cv2") is None:  # pragma: no cover
    cv2 = None
else:
    cv2 = importlib.import_module("cv2")


class OpenCVCamera:
    """OpenCV-backed frame source suitable for local prototyping and Pi deployment."""

    def __init__(self, source: int | str = 0, name: str = "camera0") -> None:
        self.source = source
        self.name = name
        self._capture: Any | None = None

    def open(self) -> None:
        if cv2 is None:
            msg = "opencv-python-headless is not installed"
            raise RuntimeError(msg)
        self._capture = cv2.VideoCapture(self.source)
        if not self._capture.isOpened():
            msg = f"failed to open camera source {self.source!r}"
            raise RuntimeError(msg)

    def read(self) -> Any:
        if self._capture is None:
            self.open()
        assert self._capture is not None
        ok, frame = self._capture.read()
        if not ok:
            msg = "failed to read frame from camera source"
            raise RuntimeError(msg)
        return frame

    def capture_frame(self) -> FramePacket:
        return FramePacket(image=self.read(), source=self.name, frame_id=str(uuid4()))

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


class ImageFileCamera:
    """Small helper for replaying still frames from disk during development."""

    def __init__(self, image_path: Path, name: str = "image-file") -> None:
        self.image_path = image_path
        self.name = name

    def capture_frame(self) -> FramePacket:
        if cv2 is None:
            msg = "opencv-python-headless is not installed"
            raise RuntimeError(msg)
        frame = cv2.imread(str(self.image_path))
        if frame is None:
            msg = f"failed to read image file {self.image_path}"
            raise RuntimeError(msg)
        return FramePacket(image=frame, source=self.name, frame_id=self.image_path.stem)
