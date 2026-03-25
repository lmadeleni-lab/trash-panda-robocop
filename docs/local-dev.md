# Local Development

## Install

```bash
make install
```

## Run the API

```bash
make run
```

## Run the simulation replay

```bash
make simulate
```

## Run the checks

```bash
make lint
make typecheck
make test
```

## Useful Files

- `configs/simulation.yaml` for permissive local simulation settings
- `src/raccoon_guardian/simulation/sample_events.py` for canned night scenarios
- `tests/test_simulation.py` for end-to-end replay coverage

## Notes

- The default setup uses mock actuators
- The SQLite database is created automatically under `data/`
- The test actuation endpoint is disabled unless `allow_test_actuation` is enabled in config
- Annotated frame captures are saved under the configured `perception.capture_dir`
