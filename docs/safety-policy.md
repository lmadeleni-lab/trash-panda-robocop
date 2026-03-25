# Safety Policy

This repository is intentionally opinionated. The safety layer is a hard-coded gate that cannot be bypassed by the strategy catalog, the API, or any future OpenClaw client.

## Immutable Constraints

- Never actuate on humans
- Never actuate on pets
- Never actuate when manual disable is set
- Never actuate outside configured arm hours
- Never actuate outside deterrence-enabled geofenced zones
- Never exceed configured water duration caps
- Never exceed configured sound duration caps
- Never exceed configured pan angle bounds
- Never actuate during cooldown
- Always preserve a safe retreat path and avoid cornering behavior

## Explicitly Out of Scope

The system must not implement:

- trapping
- netting
- physical barriers that close behind the animal
- chasing or pursuit motion
- harmful contact
- chemicals
- heat
- lasers
- flame

## Decision Trace Contract

Every decision returns a structured trace containing:

- rule identifier
- allow or deny result
- human-readable explanation

Example:

```json
[
  {"rule": "arm_window", "allowed": true, "message": "Current time falls inside the arm window."},
  {"rule": "human_exclusion", "allowed": true, "message": "Target is not classified as human."},
  {"rule": "zone_geofence", "allowed": false, "message": "Zone outside is not deterrence-enabled."}
]
```

## Operational Expectations

- Keep the water spray brief and directional only toward the monitored boundary zone, not the animal
- Keep sound cues short to reduce neighborhood nuisance
- Use strobing patterns conservatively
- Prefer retreat encouragement over escalation
- Review false positives and nuisance metrics before changing default strategy

