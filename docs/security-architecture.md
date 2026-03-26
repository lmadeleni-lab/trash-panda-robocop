# Security Architecture

This project is designed so that a third party on the network should not be able to casually take control of the rover, read sensitive operational state, or access future camera-control surfaces without passing multiple gates.

## Threat Model

Primary concerns:

- unauthorized control of rover behavior
- unauthorized access to future camera or sensor-control endpoints
- unauthorized access to event history, schedules, or operator briefings
- abuse of the OpenClaw-facing interface
- lateral movement from an untrusted client on the same local network

## Current Protection Layers

### 1. Trusted Network Boundary

Sensitive routes can be restricted to configured trusted client CIDR ranges.

Config:

```yaml
security:
  trusted_network_required: true
  trusted_client_cidrs:
    - 127.0.0.1/32
    - ::1/128
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
```

When enabled, clients outside these ranges are denied before they can read sensitive operational data or issue control commands.

### 2. API Key Protection

Mutating routes and OpenClaw control routes require `X-API-Key` when API key protection is enabled.

This protects:

- arming and disarming
- mock event injection
- strategy selection
- morning summary delivery
- escalation
- guard-round execution
- agent-cycle execution
- OpenClaw control surfaces

### 3. Sensitive Read Gating

Read endpoints that expose operational state or audit data are also protected by the trusted-network boundary.

This includes:

- `/status`
- `/scheduler`
- `/config`
- `/events`
- `/strategies`
- `/strategies/recommendations`
- `/summary/nightly`
- `/agents/status`
- `/agents/reports`

### 4. Safety Boundary On The Pi

Even an authorized client does not get unrestricted hardware control.

The Raspberry Pi field node still enforces:

- human exclusion
- pet exclusion
- hazard safe-park behavior
- cooldowns
- geofencing
- actuation duration caps
- approved strategy catalog only

## Camera And Sensor Control

There is no public unrestricted camera-control API in this repo.

Future camera or live-view features should inherit the same gates:

- trusted-network-only access
- API-key protection
- minimal scope
- audit logging

Recommended stance:

- do not expose raw camera-control endpoints to the public internet
- keep camera surfaces on a trusted LAN or VPN only
- treat camera orientation, stream access, and capture triggers as sensitive operations

## OpenClaw Containment

OpenClaw is intentionally boxed in.

It may:

- read bounded briefings
- read summaries
- list approved strategies
- set the next approved strategy

It may not:

- issue direct camera commands
- issue arbitrary actuator commands
- bypass the Pi safety policy
- change security or safety settings

## Operational Hardening Recommendations

- bind the Pi API only to a trusted LAN or VPN
- set `trusted_network_required: true` on field deployments
- set a strong `RG_API_KEY`
- rotate API keys when operator devices change
- keep the Mac mini and Pi on a private management network if possible
- do not port-forward the field API directly to the public internet
- review rotating JSON logs regularly

## Logging And Auditability

The runtime logs:

- request path
- request method
- request status code
- request duration
- request ID
- controller decisions
- scheduler actions
- mission-agent cycles

This is important for quickly diagnosing attempted misuse or unexpected access.

## Future Hardening

Good next steps:

- mutual TLS or reverse-proxy auth in front of the Pi API
- separate operator and service API keys
- signed command envelopes for remote control surfaces
- camera stream tokenization and short-lived session grants
- explicit webhook signing for external integrations
