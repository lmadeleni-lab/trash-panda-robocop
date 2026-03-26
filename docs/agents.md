# Mission Agents

`trash-panda Robocop` now includes a bounded autonomous review layer intended to make the system easier to operate, debug, and improve between nights.

These agents do **not** bypass the field-node safety policy and they do **not** self-modify the live robot. Their job is to review outcomes, flag operational issues, and propose next steps.

## Included Agents

### `nightly_review`

Purpose:

- review the latest nightly summary
- compare current strategy against observed effectiveness
- highlight repeated failures or cleanup hotspots

Outputs:

- findings about failed deterrence or low activity
- proposals for strategy review
- zone cleanup suggestions when droppings hotspots appear

### `health_monitor`

Purpose:

- inspect the runtime operating posture
- flag security and scheduler issues
- warn when the node is disarmed or under-configured

Outputs:

- findings about API key posture
- findings about armed/disarmed state
- proposals to verify summary delivery or scheduler behavior

### `mission_improvement`

Purpose:

- scan recent outcome history
- identify recurring gaps in perception, nuisance, or coverage
- build a persistent improvement backlog

Outputs:

- feature candidates
- skill candidates
- operational drills or calibration work

## Design Boundaries

Allowed:

- reading encounter history
- reading summaries
- recommending strategy changes
- generating feature and skill proposals
- optionally selecting the next approved strategy if explicitly enabled in config

Not allowed:

- changing safety caps
- issuing arbitrary actuator commands
- editing code automatically
- deploying changes automatically
- bypassing human, pet, or hazard protections

## Persistence

Agent reports are stored in SQLite alongside encounters.

Stored fields include:

- agent name
- summary
- findings
- proposals
- metadata
- creation timestamp

This makes agent output auditable and easy to inspect over time.

## Runtime

Agent cycles are controlled by the `agents` config block:

```yaml
agents:
  enabled: true
  run_interval_minutes: 60
  auto_strategy_selection: false
  max_recent_outcomes: 100
```

When background scheduling is enabled, the runtime loop can execute the agent cycle automatically at the configured cadence.

## API

- `GET /agents/status`
- `GET /agents/reports`
- `POST /agents/run`

## MVP Positioning

For MVP, these agents are best understood as:

- persistent operators
- automated reviewers
- backlog generators

They are not autonomous software developers. They help the mission by creating a durable stream of operational intelligence and concrete next-step proposals while the human team remains in control of code changes and field deployment.
