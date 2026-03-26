# Production Checklist

## Security

- [ ] `security.api_key_enabled` is set to `true`
- [ ] `RG_API_KEY` is supplied through environment, not committed config
- [ ] `RG_SLACK_WEBHOOK_URL` is supplied through environment if Slack is used
- [ ] app is reachable only on a trusted LAN or VPN

## Hardware

- [ ] physical kill switch tested
- [ ] actuator rails fused and isolated
- [ ] water spray aimed at threshold zone, not directly at animals
- [ ] light and sound do not overspill into neighboring property
- [ ] pan or arm-head presets stay within bounded motion envelope

## Perception

- [ ] gate and pool-edge zones calibrated from final camera mount
- [ ] nighttime exposure and glare tested
- [ ] false-positive review completed with at least one full-night simulation or dry run

## Operations

- [ ] morning summary enabled and reviewed
- [ ] `runtime.background_scheduler_enabled` enabled on unattended nodes
- [ ] `agents.enabled` verified and `/agents/status` reviewed
- [ ] Slack escalation path tested
- [ ] droppings cleanup heatmap reviewed in summary output
- [ ] guard round presets verified for stationary scan coverage
- [ ] service auto-restart behavior tested
- [ ] rotating log file path verified under `data/logs/`

## Safety

- [ ] human exclusion tested
- [ ] pet exclusion tested
- [ ] hazard hide mode tested for bear-class detection
- [ ] manual disable path tested
- [ ] cooldown behavior verified
