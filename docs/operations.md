# Operations

This document describes how `trash-panda Robocop` is intended to behave in a production-minded deployment.

## Operating Modes

| Mode | Purpose | Notes |
| --- | --- | --- |
| Disarmed | No deterrence allowed | Safe default for maintenance and daytime setup |
| Armed idle | Waiting for detections during allowed hours | Camera and logging stay available |
| Detecting | Reviewing incoming target events | Can use mock, motion, or model-backed detectors |
| Acting | Running a bounded deterrence strategy | Light, sound, water, and optional fixed-base repositioning only |
| Cooldown | Suppressing repeated nuisance triggers | Prevents rapid repeated output |
| Safe-park / hide mode | Triggered by hazard-class wildlife such as a bear | Stops outputs and disarms the node |

## Stationary Guard Rounds

Guard rounds are supported only as *stationary scan presets*. The system may:

- move a pan head or arm-mounted cluster between a few small preset angles
- sweep camera focus across gate and pool-edge sectors
- check that the protected zones are still visually clear

The system must not:

- drive toward animals
- chase, follow, or close distance
- use motion to block a retreat path

## Morning Summary

The production-oriented control loop includes a nightly review artifact that is intended to be delivered each morning.

Recommended content:

- total events
- target breakdown by species or class
- acted versus denied events
- failed deterrence count
- top-performing strategy
- notable recurrence events

The repository includes a morning summary service and Slack delivery path, but leaves scheduling to deployment tooling or an external automation layer.

## Species-Aware Strategy Selection

Different target classes can prefer different safe strategies. The first version supports target-specific strategy preferences such as:

- raccoon -> `LIGHT_WATER`
- unknown -> `LIGHT_ONLY`

These preferences remain bounded by the same human/pet exclusion, geofence, cooldown, and duration caps.

## Slack Escalation

If deterrence appears ineffective, the system can send a Slack escalation through an incoming webhook. Suggested escalation triggers:

- no retreat detected
- returned within 10 minutes
- repeated same-night return

Slack alerts should be concise and action-oriented:

- target class
- zone
- recent failure count
- recommended operator review action

## Chat-Based Control

Chat-based control should sit *above* the existing bounded API surface. Safe chat actions include:

- arm or disarm
- request nightly summaries
- list strategies
- select the next approved strategy
- inspect recent outcomes

Unsafe chat actions should remain disallowed:

- arbitrary actuator timing
- arbitrary movement or sweep commands
- changes that bypass safety policy

