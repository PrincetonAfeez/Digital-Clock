# PyClock Schema Folder

This `Schema/` folder contains simple JSON Schema files for the PyClock repository (`PrincetonAfeez/Digital-Clock`). They document and validate the main data contracts used by the app:

- `pyclock-config.schema.json` — JSON-shape schema for the TOML config at `~/.pyclock/config.toml`.
- `pyclock-alarm.schema.json` — schema for persisted alarms in `~/.pyclock/alarms.json`.
- `pyclock-session.schema.json` — schema for each JSON Lines record in `~/.pyclock/sessions.jsonl`.
- `pyclock-state.schema.json` — schema for the in-memory clock state shape.
- `pyclock-cli.schema.json` — schema for normalized CLI command requests.
- `schema-index.json` — a small manifest for the schema package.

These schemas are intentionally lightweight and do not add runtime dependencies to PyClock. Copy this folder into the repository root when you want schema documentation alongside the source code.

## Notes

PyClock reads TOML for configuration, but JSON Schema validates JSON-like objects. To validate `config.toml`, first load TOML into a Python dictionary, then validate the resulting object against `pyclock-config.schema.json`.

## Optional validation example

```bash
python -m pip install jsonschema
python - <<'PY'
import json
from pathlib import Path
from jsonschema import validate

schema = json.loads(Path('Schema/pyclock-alarm.schema.json').read_text())
data = json.loads(Path('Schema/examples/alarm.example.json').read_text())
validate(instance=data, schema=schema)
print('alarm.example.json is valid')
PY
```

For `sessions.jsonl`, validate each line separately using `pyclock-session.schema.json`.
