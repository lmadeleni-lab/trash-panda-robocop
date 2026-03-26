# Heartbeat

If this agent is used in a scheduled heartbeat flow:

1. call `trash_panda_briefing`
2. report whether:
   - the Pi is armed or disarmed
   - the scheduler is enabled
   - the last morning summary delivered successfully
   - guard rounds appear to be running
   - recent failures suggest a human should review the system
3. if deterrence failures are repeated, recommend a human follow-up
4. do not change strategy automatically unless the heartbeat task explicitly permits it
