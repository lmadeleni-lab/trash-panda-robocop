# Tool Notes

The Mac mini OpenClaw agent is expected to use the local plugin tools that proxy into the Raspberry Pi field node.

## Primary Tool Sequence

For most operator conversations:

1. `trash_panda_briefing`
2. `trash_panda_list_strategies` if strategy context is needed
3. `trash_panda_set_strategy` only when there is a justified next-step change

## What Each Tool Is For

- `trash_panda_briefing`
  - use first for a combined operator snapshot
  - includes system status, scheduler status, recommendation map, recent outcomes, and a nightly summary
- `trash_panda_list_strategies`
  - use when the operator asks what options exist
- `trash_panda_get_summary`
  - use when the operator asks for a specific date
- `trash_panda_set_strategy`
  - use only after explaining why the change is appropriate

## Do Not Do

- do not set strategy blindly
- do not repeat tool calls unless new information is needed
- do not present raw JSON without summarizing it for the operator
