# Mac Mini OpenClaw Plugin

This plugin is meant to run on a local OpenClaw machine such as a Mac mini on the same trusted LAN as the Raspberry Pi field node.

## Intended Topology

- `Mac mini`: OpenClaw gateway, operator chat surface, bounded strategy selection
- `Raspberry Pi`: camera, GPIO-adjacent actuators, local FastAPI service, event store
- `Network`: trusted LAN or VPN only

## Install

From the Mac mini:

```bash
cd /path/to/trash-panda-robocop/integrations/opencclaw/mac-mini-plugin
npm install
openclaw plugins install -l "$(pwd)"
```

Then point the plugin at the Raspberry Pi service in `~/.openclaw/openclaw.json`.

Example:

```json
{
  "plugins": {
    "enabled": true,
    "entries": {
      "trash-panda-robocop": {
        "enabled": true,
        "config": {
          "baseUrl": "http://trash-panda-pi.local:8000",
          "apiKey": "replace-with-the-pi-rg-api-key",
          "requestTimeoutMs": 5000
        }
      }
    }
  },
  "tools": {
    "allow": [
      "trash_panda_briefing",
      "trash_panda_list_strategies",
      "trash_panda_get_summary",
      "trash_panda_set_strategy"
    ]
  }
}
```

## What It Exposes

- `trash_panda_briefing`
- `trash_panda_list_strategies`
- `trash_panda_get_summary`
- `trash_panda_set_strategy`

It does not expose direct actuation or test-fire tools.

## Pair It With The Agent Pack

For a much cleaner operator experience on the Mac mini, pair this plugin with the workspace pack in [../mac-mini-agent/README.md](/Users/laurent/Development/trash-panda-robocop/integrations/opencclaw/mac-mini-agent/README.md).

That gives OpenClaw:

- a specific operator persona
- a required `briefing-first` workflow
- explicit rules for when strategy changes are justified
- a heartbeat routine for daily review
