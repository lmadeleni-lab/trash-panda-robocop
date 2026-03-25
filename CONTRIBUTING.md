# Contributing

Thanks for your interest in improving `trash-panda Robocop`.

This project is open to contributions, but safety and clarity come before novelty. The system is intentionally scoped to humane, non-contact deterrence with strong guardrails, and contributions should preserve that posture.

## First Principles

- Keep the system humane and non-contact
- Do not add trapping, pursuit, cornering, pain compliance, chemicals, heat, lasers, or flame
- Treat the safety policy as non-bypassable
- Prefer simulation-first changes before hardware integration
- Be explicit about what is mocked, stubbed, or production-ready

## Good Contribution Areas

- detector backends and perception tooling
- better simulation scenarios and replay tooling
- improved logging, summaries, and evaluation metrics
- safer hardware abstraction layers
- documentation, tests, diagrams, and onboarding polish

## Before You Open a PR

1. Open an issue for larger design changes
2. Keep the writeup honest about hardware maturity and deployment assumptions
3. Add or update tests when behavior changes
4. Run the local checks:

```bash
make lint
make typecheck
make test
```

## Pull Request Expectations

- small, reviewable diffs are preferred
- safety implications should be called out explicitly
- new hardware code should keep mock implementations available
- APIs and tools should remain bounded and auditable

## Areas Requiring Extra Care

- anything that changes the safety decision path
- anything that changes actuator timing or bounds
- anything that increases nuisance risk to neighbors
- anything that expands OpenClaw or external-agent control

## Development Workflow

```bash
make install
make run
make simulate
```

Useful docs:

- [README.md](/Users/laurent/Development/trash-panda-robocop/README.md)
- [docs/architecture.md](/Users/laurent/Development/trash-panda-robocop/docs/architecture.md)
- [docs/safety-policy.md](/Users/laurent/Development/trash-panda-robocop/docs/safety-policy.md)
- [ROADMAP.md](/Users/laurent/Development/trash-panda-robocop/ROADMAP.md)

