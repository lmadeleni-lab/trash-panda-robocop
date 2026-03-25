from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

from raccoon_guardian.domain.models import EncounterRecord
from raccoon_guardian.storage.db import init_db


class EventRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        init_db(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def record_encounter(self, record: EncounterRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO encounters (
                    encounter_id, timestamp, target_class, zone_id, is_human, is_pet,
                    chosen_strategy, allowed, state_before, state_after, detection_json,
                    decision_json, actions_json, outcome_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.encounter_id,
                    record.detection.timestamp.isoformat(),
                    record.detection.target_class.value,
                    record.detection.zone_id.value,
                    int(record.detection.is_human),
                    int(record.detection.is_pet),
                    record.chosen_strategy.value if record.chosen_strategy else None,
                    int(record.decision.allowed),
                    record.state_before.value,
                    record.state_after.value,
                    record.detection.model_dump_json(),
                    record.decision.model_dump_json(),
                    json.dumps(
                        [result.model_dump(mode="json") for result in record.action_results]
                    ),
                    record.outcome.model_dump_json() if record.outcome else None,
                    record.created_at.isoformat(),
                ),
            )
            connection.commit()

    def list_encounters(self, limit: int = 100) -> list[EncounterRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM encounters ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._hydrate(row) for row in rows]

    def list_encounters_for_local_date(
        self, local_date: str, timezone_name: str
    ) -> list[EncounterRecord]:
        zone = ZoneInfo(timezone_name)
        records = self.list_encounters(limit=1_000)
        return [
            record
            for record in records
            if record.detection.timestamp.astimezone(zone).date().isoformat() == local_date
        ]

    def recent_outcomes(self, limit: int = 20) -> list[EncounterRecord]:
        return [
            record for record in self.list_encounters(limit=limit) if record.outcome is not None
        ]

    def _hydrate(self, row: sqlite3.Row) -> EncounterRecord:
        detection_json = row["detection_json"]
        decision_json = row["decision_json"]
        actions_json = row["actions_json"]
        outcome_json = row["outcome_json"]
        payload = {
            "encounter_id": row["encounter_id"],
            "detection": json.loads(detection_json),
            "state_before": row["state_before"],
            "state_after": row["state_after"],
            "chosen_strategy": row["chosen_strategy"],
            "decision": json.loads(decision_json),
            "action_results": json.loads(actions_json),
            "outcome": json.loads(outcome_json) if outcome_json is not None else None,
            "created_at": row["created_at"],
        }
        return EncounterRecord.model_validate(payload)
