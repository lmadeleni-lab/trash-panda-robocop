from __future__ import annotations

from raccoon_guardian.config import AppConfig
from raccoon_guardian.domain.enums import ZoneId


def is_zone_deterrence_enabled(config: AppConfig, zone_id: ZoneId) -> bool:
    zone = config.zone_map().get(zone_id)
    return zone is not None and zone.deterrence_enabled
