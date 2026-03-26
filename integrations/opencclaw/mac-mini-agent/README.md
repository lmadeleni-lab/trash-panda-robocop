# Mac Mini Agent Pack

This is a ready-to-copy OpenClaw workspace pack for a `trash-panda Robocop` operator agent running on a Mac mini.

It is designed for the deployment shape documented in [docs/opencclaw-integration.md](/Users/laurent/Development/trash-panda-robocop/docs/opencclaw-integration.md):

- `Mac mini`: OpenClaw, operator chat, bounded strategy review
- `Raspberry Pi`: camera, safety policy, local event store, actuators

## What This Pack Includes

- `AGENTS.md`: operating instructions and decision rules
- `SOUL.md`: tone, persona, and boundaries
- `TOOLS.md`: how to use the bounded trash-panda tools
- `HEARTBEAT.md`: optional recurring check routine

## Install On The Mac Mini

```bash
cd /path/to/trash-panda-robocop/integrations/opencclaw/mac-mini-agent
./install.sh
```

That will create or update:

- `~/.openclaw/workspace-trash-panda-robocop/AGENTS.md`
- `~/.openclaw/workspace-trash-panda-robocop/SOUL.md`
- `~/.openclaw/workspace-trash-panda-robocop/TOOLS.md`
- `~/.openclaw/workspace-trash-panda-robocop/HEARTBEAT.md`

Then point OpenClaw at that workspace in `~/.openclaw/openclaw.json`.

## Suggested OpenClaw Config

Use the plugin sample in [openclaw.sample.json](/Users/laurent/Development/trash-panda-robocop/integrations/opencclaw/openclaw.sample.json), plus the workspace path below:

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.openclaw/workspace-trash-panda-robocop"
    }
  }
}
```

## Operating Model

This agent should:

- start with `trash_panda_briefing`
- review recent outcomes before changing strategy
- prefer de-escalation when simpler strategies are effective
- refuse any request for direct hardware control
- escalate to a human operator if repeated deterrence fails or hazard wildlife is involved
