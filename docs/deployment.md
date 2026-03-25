# Deployment

This repository is still an alpha starter kit, but it now includes enough structure to support a serious Raspberry Pi staging environment.

## Recommended Topology

- Raspberry Pi 5 or Pi 4B in a weather-aware enclosure
- local FastAPI process bound to a trusted network interface
- API key enabled for all control endpoints
- Slack webhook configured through environment variables, not committed YAML
- systemd-managed service for automatic restart
- background scheduler enabled for autonomous guard rounds and morning summary delivery

## Required Environment Variables

```bash
RG_CONFIG_PATH=configs/backyard-gate-example.yaml
RG_LOG_LEVEL=INFO
RG_HOST=0.0.0.0
RG_PORT=8000
RG_API_KEY=replace-with-a-long-random-secret
RG_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

## Local Production-Like Run

```bash
make install
export RG_CONFIG_PATH=configs/backyard-gate-example.yaml
export RG_API_KEY="$(openssl rand -hex 24)"
uv run python -m raccoon_guardian.app
```

The `backyard-gate-example.yaml` profile enables the background scheduler. That means the running service can perform stationary guard rounds during the armed window and deliver morning summaries on its own without an external cron job.

## Control Surface Hardening

Mutating endpoints are now designed to sit behind an `X-API-Key` header when API key protection is enabled.

Examples:

```bash
curl -H "X-API-Key: $RG_API_KEY" http://127.0.0.1:8000/status
curl -X POST -H "X-API-Key: $RG_API_KEY" http://127.0.0.1:8000/arm
curl -X POST -H "X-API-Key: $RG_API_KEY" http://127.0.0.1:8000/guard-rounds/run
```

## systemd

Reference service files live under `deploy/systemd/`.

Suggested install flow on the Pi:

1. copy the repo to `/opt/trash-panda-robocop`
2. create a dedicated service user
3. create an environment file with `RG_API_KEY` and `RG_SLACK_WEBHOOK_URL`
4. install the systemd unit
5. enable and start the service

## Readiness Endpoints

- `GET /health`
- `GET /health/ready`
- `GET /status`
- `GET /scheduler`

Use `ready` and `status` as the first stop during staging and incident response.
