from __future__ import annotations

from raccoon_guardian.config import ZoneConfig
from raccoon_guardian.domain.enums import DirectionOfTravel, ZoneId
from raccoon_guardian.domain.models import NormalizedBBox


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < ((xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi)
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def zone_for_bbox(bbox: NormalizedBBox, zones: list[ZoneConfig]) -> ZoneId:
    center = bbox.center()
    for zone in zones:
        if point_in_polygon(center, zone.polygon):
            return zone.zone_id
    return ZoneId.OUTSIDE


def infer_direction(
    previous_bbox: NormalizedBBox | None, current_bbox: NormalizedBBox
) -> DirectionOfTravel:
    if previous_bbox is None:
        return DirectionOfTravel.UNKNOWN
    previous_x, _ = previous_bbox.center()
    current_x, _ = current_bbox.center()
    delta = current_x - previous_x
    if delta > 0.05:
        return DirectionOfTravel.INBOUND
    if delta < -0.05:
        return DirectionOfTravel.OUTBOUND
    return DirectionOfTravel.LATERAL
