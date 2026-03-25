from __future__ import annotations

from pathlib import Path

from raccoon_guardian.config import load_config
from raccoon_guardian.domain.enums import DirectionOfTravel, ZoneId
from raccoon_guardian.domain.models import NormalizedBBox
from raccoon_guardian.perception.zone_logic import infer_direction, zone_for_bbox


def test_zone_for_bbox_returns_gate_entry() -> None:
    config = load_config(Path("configs/simulation.yaml"))
    bbox = NormalizedBBox(x1=0.10, y1=0.50, x2=0.20, y2=0.60)
    assert zone_for_bbox(bbox, config.zones) == ZoneId.GATE_ENTRY


def test_infer_direction_detects_inbound_motion() -> None:
    previous = NormalizedBBox(x1=0.10, y1=0.50, x2=0.20, y2=0.60)
    current = NormalizedBBox(x1=0.30, y1=0.50, x2=0.40, y2=0.60)
    assert infer_direction(previous, current) == DirectionOfTravel.INBOUND
