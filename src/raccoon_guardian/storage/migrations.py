from __future__ import annotations

SCHEMA_VERSION = 2


def schema_statements() -> list[str]:
    return [
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS encounters (
            encounter_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            target_class TEXT NOT NULL,
            zone_id TEXT NOT NULL,
            is_human INTEGER NOT NULL,
            is_pet INTEGER NOT NULL,
            chosen_strategy TEXT,
            allowed INTEGER NOT NULL,
            state_before TEXT NOT NULL,
            state_after TEXT NOT NULL,
            detection_json TEXT NOT NULL,
            decision_json TEXT NOT NULL,
            actions_json TEXT NOT NULL,
            outcome_json TEXT,
            created_at TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_encounters_timestamp ON encounters(timestamp)",
        """
        CREATE TABLE IF NOT EXISTS agent_reports (
            report_id TEXT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            summary TEXT NOT NULL,
            findings_json TEXT NOT NULL,
            proposals_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_agent_reports_created_at ON agent_reports(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_agent_reports_agent_name ON agent_reports(agent_name)",
    ]
