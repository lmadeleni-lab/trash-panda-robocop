# Fleet Sentry

This version adds a bounded `sentry` layer and a `fleet` coordination layer for multi-bot perimeter coverage.

## What It Adds

- scheduled local patrol paths
- path selection influenced by area assignment and recent zone pressure
- multi-bot area coordination
- regroup mode
- staggered multi-angle zone observation
- bounded stuck recovery planning

## Safety Boundary

This is still **not** a pursuit system.

Allowed:

- pre-scheduled patrols
- fixed observation posts
- regroup to a safe preset
- staggered views of a hot zone
- bounded recovery motions when a bot is stuck

Not allowed:

- target chasing
- cornering
- surrounding a live animal
- multi-bot convergence on a live target
- aggressive mobility escalation

The coordination notes and config explicitly keep the system in `zone coverage` mode rather than `target pursuit` mode.

## Core Concepts

### Patrol Path

A patrol path is a named sequence of waypoints. Each waypoint contains:

- zone
- observation preset
- bounded linear move
- bounded turn
- dwell time
- pan servo target

### Fleet Plan

A fleet plan assigns:

- primary bot per zone
- optional supporting bots per zone
- a local bot mode
- a local path
- regroup instructions when needed

### Recovery Plan

If a bot reports `mobility_state=stuck`, the system can produce a bounded recovery plan:

1. safe stop
2. short reverse
3. slight turn
4. safe stop
5. regroup recommendation

## API

### Sentry

- `GET /sentry/status`
- `POST /sentry/run`

### Fleet

- `GET /fleet/status`
- `GET /fleet/coordination`
- `POST /fleet/bots/heartbeat`
- `POST /fleet/regroup`
- `GET /fleet/recovery/{bot_id}`

## Config Surface

Key sections:

- `sentry`
- `fleet`
- `recovery`

Example features in the sample configs:

- `sim_perimeter`
- `backyard_scout`
- multi-bot area assignments
- regroup preset
- bounded motion and recovery timings

## How Path Selection Works

For MVP, the local path is selected from:

1. configured bot area assignments
2. recent encounter pressure by zone
3. configured patrol paths that best match those zones

The current planner is intentionally simple and auditable. It is designed to be improved over time by the mission-agent review layer without letting agents invent arbitrary movement patterns.

## Multi-Angle Observation

The fleet planner can assign supporting bots to a hot zone, but only for offset observation posts.

That means:

- different viewpoints on the same zone
- no closing on a live target
- no surrounding behavior

## Stuck Handling

Bots can report:

- `nominal`
- `degraded`
- `stuck`

When stuck:

- recovery is bounded
- regroup may be requested
- other bots can continue coverage in their assigned areas

## MentorPi Fit

This layer is designed to pair with the MentorPi ROS2 bridge scaffold in:

- [mentorpi_ros2.py](/Users/laurent/Development/trash-panda-robocop/src/raccoon_guardian/integrations/mentorpi_ros2.py)

That bridge turns waypoint moves and recovery actions into bounded ROS2 command payloads suitable for later wiring into the vendor stack.
