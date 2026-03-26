# OpenClaw Integration

This repository reserves the strategy layer for approved, bounded choices only. OpenClaw can participate as a reader and selector, but not as an unrestricted hardware controller.

## Recommended Deployment Shape

The cleanest field architecture is:

- `Raspberry Pi` at the gate or pool boundary
- `Mac mini` on the same trusted LAN running OpenClaw
- `FastAPI` on the Pi exposing only the bounded trash-panda Robocop control surface
- `X-API-Key` shared from the Pi service to the Mac mini plugin

That keeps the camera, actuator timing, and safety enforcement local to the Pi while leaving strategy review, chat interaction, and operator workflow on the Mac mini.

## Allowed Operations

An OpenClaw-connected client may:

- read recent encounter outcomes
- list approved strategies
- set the current strategy for the next event window
- request nightly summaries

It may not:

- send arbitrary actuator commands
- change safety caps
- change arm windows
- bypass cooldown
- issue unrestricted pan or sweep motions

## Bounded Tool Model

The adapter in `src/raccoon_guardian/tools/opencclaw_adapter.py` wraps only these functions:

- `get_recent_outcomes(limit)`
- `list_strategies()`
- `set_next_strategy(strategy_name)`
- `get_nightly_summary(local_date)`
- `get_briefing(limit, local_date)`

Each function operates entirely above the safety boundary.

The FastAPI service now also exposes bounded agent-facing endpoints:

- `GET /agent/opencclaw/manifest`
- `GET /agent/opencclaw/briefing`

## Integration Sequence

```mermaid
sequenceDiagram
    participant OC as OpenClaw (Mac mini)
    participant API as Pi FastAPI / Tools
    participant Store as SQLite Store
    participant Ctrl as Controller

    OC->>API: briefing() / nightly_summary()
    API->>Store: read recent encounters
    Store-->>API: encounter outcomes + rankings
    API-->>OC: bounded briefing payload
    OC->>API: set_next_strategy(LIGHT_WATER)
    API->>Ctrl: update selected strategy
    Ctrl-->>API: acknowledged
    API-->>OC: success
```

## Guardrails

- The selected strategy must exist in the fixed catalog
- The strategy affects only future events
- Safety policy is evaluated again at event time
- Encounter outcomes stay locally logged for auditability

## Mac Mini Setup

1. On the Raspberry Pi, run `trash-panda Robocop` with `RG_API_KEY` enabled.
2. On the Mac mini, install and configure OpenClaw.
3. Install the local plugin from `integrations/opencclaw/mac-mini-plugin/`.
4. Point the plugin at the Pi service URL and API key.
5. Restrict OpenClaw to the trash-panda tools only.

The sample plugin and config starter live here:

- `integrations/opencclaw/mac-mini-plugin/`
- `integrations/opencclaw/openclaw.sample.json`

### Suggested Pi-side settings

- use `configs/backyard-gate-example.yaml`
- set `RG_API_KEY` in the Pi environment
- bind the API only to a trusted LAN or VPN
- leave direct actuation endpoints protected

### Suggested Mac mini plugin settings

```json
{
  "plugins": {
    "enabled": true,
    "entries": {
      "trash-panda-robocop": {
        "enabled": true,
        "config": {
          "baseUrl": "http://trash-panda-pi.local:8000",
          "apiKey": "replace-with-rg-api-key",
          "requestTimeoutMs": 5000
        }
      }
    }
  },
  "tools": {
    "allow": [
      "trash_panda_briefing",
      "trash_panda_list_strategies",
      "trash_panda_get_summary",
      "trash_panda_set_strategy"
    ]
  }
}
```

## Recommended Operating Pattern

1. Start with `LIGHT_ONLY` or `LIGHT_SOUND`
2. Review nightly summaries for false positives and nuisance score
3. Escalate only within the approved catalog if recurrence remains high
4. De-escalate when simpler strategies are effective
