from __future__ import annotations

from pathlib import Path

from raccoon_guardian.config import load_config
from raccoon_guardian.domain.enums import ZoneId


def test_load_config_has_required_zones() -> None:
    config = load_config(Path("configs/simulation.yaml"))
    zone_ids = {zone.zone_id for zone in config.zones}
    assert ZoneId.GATE_ENTRY in zone_ids
    assert ZoneId.BACKYARD_PROTECTED in zone_ids
    assert config.selected_strategy.value == "LIGHT_SOUND"
