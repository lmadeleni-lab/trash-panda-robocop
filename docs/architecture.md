# Architecture

`raccoon-guardian` is organized around a narrow control loop:

1. Perception produces structured detections
2. Safety decides whether any deterrence is permitted
3. The controller selects one approved strategy
4. Mock or real actuator drivers execute bounded commands
5. Outcomes are logged and scored for later adaptation

## Technical Diagram

![trash-panda Robocop technical diagram](/Users/laurent/Development/trash-panda-robocop/docs/assets/trash-panda-robocop-technical-diagram.png)

## Component Diagram

```mermaid
flowchart TD
    subgraph EdgeNode["Raspberry Pi Edge Node"]
        Camera["Camera Interface"]
        Capture["Frame Snapshot Writer"]
        Detector["Detector Interface"]
        Zones["Zone Logic"]
        Controller["Controller"]
        SM["State Machine"]
        Safety["Safety Policy"]
        Strategy["Strategy Catalog"]
        Actuators["Actuator Hub"]
        Store["SQLite Event Store"]
        API["FastAPI API"]
        Eval["Strategy Evaluator"]
    end

    Camera --> Detector
    Camera --> Capture
    Detector --> Zones
    Zones --> Controller
    Controller --> SM
    Controller --> Safety
    Controller --> Strategy
    Strategy --> Actuators
    Safety -->|allow or deny| Controller
    Controller --> Store
    Capture --> Store
    Store --> Eval
    API --> Controller
    API --> Store
    Eval --> API

    OpenClaw["OpenClaw Strategy Client"] --> API
    OpenClaw -->|bounded tools only| Strategy
```

## State Model

```mermaid
stateDiagram-v2
    [*] --> DISARMED
    DISARMED --> IDLE: arm
    IDLE --> DISARMED: disarm
    IDLE --> DETECTING: detection arrives
    DETECTING --> DECIDING: target present
    DETECTING --> IDLE: no actionable target
    DECIDING --> ACTING: safety allows
    DECIDING --> IDLE: safety denies
    ACTING --> COOLDOWN: bounded actuation complete
    COOLDOWN --> IDLE: cooldown elapsed
    ACTING --> ERROR: actuator failure
    DECIDING --> ERROR: unexpected failure
    ERROR --> DISARMED: operator disarm
    ERROR --> IDLE: reset
```

## Runtime Boundaries

- `perception/` converts raw frames or replay input into structured detections
- `perception/capture.py` persists raw or annotated snapshots for debugging and future dataset building
- `safety/` is the immutable policy boundary
- `strategies/` holds a fixed catalog only
- `actuators/` is where GPIO-capable drivers can be added later
- `tools/` exposes a bounded function layer for OpenClaw
- `simulation/` makes the system testable before hardware arrives

## Why the Strategy Layer Is Constrained

This project deliberately avoids autonomous action generation. The strategy layer can select only from approved named strategies whose action sequences are already reviewed and bounded. That means:

- no arbitrary actuator timing
- no arbitrary pan sweeps
- no direct hardware tool invocation by an external agent
- no path around the safety engine

## Deployment Topology

```mermaid
flowchart LR
    Sensor["Low-light Camera"] --> Pi["Raspberry Pi"]
    Pi --> DB["Local SQLite DB"]
    Pi --> Relay["Relay / MOSFET Drivers"]
    Relay --> Water["Valve / Pump Control"]
    Relay --> Light["Strobe Light"]
    Relay --> Sound["Short Audio Cue"]
    Relay --> Pan["Optional Pan Actuator"]
    Laptop["Operator Laptop"] --> API["Local FastAPI Service"]
    API --> Pi
    OpenClaw["OpenClaw Client"] --> API
```
