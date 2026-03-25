[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/api-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Simulation First](https://img.shields.io/badge/dev-simulation--first-6C757D.svg)](#simulation)

# trash-panda Robocop

![trash-panda Robocop hero](docs/assets/trash-panda-robocop-hero.svg)

`trash-panda Robocop` is the public-facing identity for the `raccoon_guardian` codebase: a production-minded starter repository for a humane, non-contact perimeter deterrence system aimed at nighttime wildlife entry events near a backyard gate or pool boundary. It is built for Raspberry Pi class hardware, but the first-class development path is simulation, image capture, and mock hardware so the project is useful before a camera, pump, light, or speaker is ever attached.

The repository assumes a safety-first operating model:

- No harmful deterrence methods
- No trapping, cornering, chasing, or physical contact
- No chemicals, heat, lasers, or flame
- A hard-coded safety layer that the strategy selector cannot bypass
- Measured adaptation only within a pre-approved catalog of bounded strategies

## What It Includes

- A deterministic state machine for `DISARMED -> IDLE -> DETECTING -> DECIDING -> ACTING -> COOLDOWN`
- A pluggable perception layer with frame capture, annotated snapshot persistence, mock detections, and model-ready detector adapters
- A non-bypassable safety policy with human and pet exclusion, geofencing, scheduling, cooldown, and action duration caps
- Mock actuator interfaces for light, sound, water spray, and optional pan motion
- A fixed catalog of approved strategies with simple effectiveness scoring
- A SQLite encounter log and nightly summary endpoint
- A bounded OpenClaw integration surface that can only read outcomes and choose from approved strategies
- FastAPI endpoints for local control and simulation

## Architecture Summary

```mermaid
flowchart LR
    Camera["Camera / Mock Events"] --> Perception["Perception Layer"]
    Perception --> Safety["Immutable Safety Policy"]
    Safety -->|allow| Controller["Controller + State Machine"]
    Safety -->|deny| Log["SQLite Event Store"]
    Controller --> Strategy["Approved Strategy Catalog"]
    Strategy --> Actuators["Bounded Actuator Hub"]
    Actuators --> Log
    Log --> Eval["Strategy Evaluator"]
    Eval --> OpenClaw["OpenClaw Adapter (bounded)"]
    Controller --> API["FastAPI Service"]
    API --> OpenClaw
```

More detail lives in [docs/architecture.md](/Users/laurent/Development/trash-panda-robocop/docs/architecture.md) and [docs/hardware.md](/Users/laurent/Development/trash-panda-robocop/docs/hardware.md).

## Quickstart

### 1. Install dependencies

```bash
make install
```

If you use `uv`, the Makefile will prefer it automatically.

### 2. Run the API locally

```bash
make run
```

The default API will listen on `127.0.0.1:8000`.

### 3. Run the night simulation

```bash
make simulate
```

This replays a sample sequence including:

- a raccoon entering the gate zone
- a cat passing by
- a person entering the yard
- a repeated raccoon return later in the night

### 4. Run quality checks

```bash
make lint
make typecheck
make test
```

## Simulation

The default experience is intentionally mock-driven:

- `MockDetector` yields structured detections
- `MockActuatorHub` records actions without touching hardware
- `NightSimulator` replays a full event sequence end-to-end
- API endpoints let you inject synthetic detections with `POST /events/mock`

This keeps local iteration fast while making room for later real camera and GPIO work.

## Perception Upgrade

The repo now includes a stronger bridge between simulation and future real-world inference:

- `FramePacket` objects for typed frame transport
- `FrameSnapshotWriter` for saving frames plus JSON metadata
- `FrameDifferenceDetector` for deterministic motion-based local testing
- `ExternalModelDetector` for future ONNX, TFLite, or remote model backends
- a perception pipeline that converts detector candidates into zone-aware `DetectionEvent` objects

The relevant modules live under [src/raccoon_guardian/perception/](/Users/laurent/Development/trash-panda-robocop/src/raccoon_guardian/perception).

## Hardware Philosophy

The target deployment is a weatherproof Raspberry Pi-based outdoor node:

- Raspberry Pi 4B or 5
- CSI or USB low-light camera
- isolated low-voltage control for water valve or pump relay
- visible strobe-capable LED module
- short-duration speaker cue path
- optional pan actuator with bounded presets only
- physical kill switch and weatherproof enclosure

Hardware planning, GPIO abstraction, power budgeting, and a suggested BOM are documented in [docs/hardware.md](/Users/laurent/Development/trash-panda-robocop/docs/hardware.md).

## Safety Controls

The hard-coded policy denies or bounds actions when any of the following are true:

- the target is a human
- the target is a pet
- the system is outside configured arm hours
- the event is outside deterrence-enabled geofenced zones
- manual disable is active
- the cooldown window has not elapsed
- requested sound or water duration exceeds configured limits

Every decision carries an explicit trace so operators can inspect why a strategy was allowed, clamped, or denied.

## OpenClaw Integration

OpenClaw is treated as an external strategy selector, not a freeform hardware controller. It may only:

- read recent outcomes
- list approved strategies
- set the next approved strategy
- request nightly summaries

It may not issue arbitrary actuator commands. See [docs/opencclaw-integration.md](/Users/laurent/Development/trash-panda-robocop/docs/opencclaw-integration.md).

## Repo Layout

```text
.
├── configs/
├── docs/
├── scripts/
├── src/raccoon_guardian/
├── tests/
└── .github/
```

## What Is Mocked vs Real

Implemented now:

- mock detector
- mock actuator hub
- FastAPI control surface
- safety engine
- SQLite encounter store
- simulation replay and tests

Still stubbed for future hardware work:

- GPIO relay control
- actual solenoid / pump driver integration
- real audio playback backend
- servo / pan hardware control
- production ML wildlife detector
- camera calibration for deployment-specific geofences

## Next Steps

- Replace the mock detector with a real low-light wildlife detection pipeline
- Add image snapshot retention with privacy-aware redaction policies
- Introduce hardware-in-the-loop tests on Raspberry Pi
- Build richer nightly adaptation logic on top of the bounded strategy interface
