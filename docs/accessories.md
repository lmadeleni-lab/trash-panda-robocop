# Accessories

This accessory matrix is intended to help move the platform closer to a production-minded outdoor node while preserving humane, non-contact behavior.

## Accessory Matrix

| Accessory | Status | Purpose | Safety Notes |
| --- | --- | --- | --- |
| Low-light camera | Recommended | Detect gate and pool-edge activity | Respect privacy and field-of-view boundaries |
| Visible strobe light | Recommended | Encourage retreat with low-contact signaling | Avoid overspill into neighboring properties |
| Weather-resistant speaker | Recommended | Short cue playback | Keep cues brief and low nuisance |
| Water spray nozzle | Recommended | Brief directional threshold spray | Aim at the zone, not directly at the animal |
| Fixed-base pan head | Recommended | Small preset repositioning and guard rounds | No pursuit or blocking behavior |
| Kill switch | Required | Cuts actuator path immediately | Prefer hardware power-path cut |
| Isolated relay or MOSFET driver | Required | Protects Pi from actuator loads | One bounded channel per output |
| Pool-edge zone calibration | Recommended | Protects pool boundary and nearby gate path | Re-check after camera remount or yard changes |
| Diffuse air puff module | Experimental | Very light threshold disturbance | Non-default, low force, heavily bounded |
| Arm-mounted cluster | Conditional | Keeps camera/light/nozzle aligned on a fixed base | Use only for small preset moves |

## Suggested Arm or Head Cluster

If the platform uses an arm or head cluster, keep it simple:

- camera
- visible light
- optional water nozzle
- optional speaker mount

This cluster should behave more like a *turreted sensor head* than a manipulator. Keep the motion envelope small and the presets auditably bounded.

## Production-Readiness Notes

- prefer weatherproof connectors and strain relief
- keep serviceable access to nozzles and relay channels
- default all outputs to off on reboot
- keep camera, water, and speaker zones inside the property perimeter
- test every accessory path in simulation and dry-run mode before live activation

