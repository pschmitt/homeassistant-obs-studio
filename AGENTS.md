# Agent instructions

## Project

This Home Assistant integration connects to OBS Studio through the OBS WebSocket v5 protocol and exposes stream, recording, scene, and system status.

## Working in this repository

- Read `README.md` before changing the WebSocket protocol mapping, entities, or available controls.
- Keep entity state and attributes aligned with OBS's reported state; do not infer that an output is active from configuration alone.
- Before changing CI, check [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) for reusable components and preserve this repository's existing checks.

## Validation

- Run `uvx ruff check .` and `uvx ruff format --check .` for Python changes.
- CI runs Hassfest and the shared Ruff checks; it currently has no test job.
