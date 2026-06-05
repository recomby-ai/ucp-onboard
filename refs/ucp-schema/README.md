# Vendored UCP JSON Schemas

Pristine copies of the official UCP JSON Schemas, used by `ucp-validate` to run
**offline** schema validation of a discovery profile (no network needed at
validation time).

## Provenance

- Source: https://github.com/Universal-Commerce-Protocol/ucp
- Tag: `v2026-04-08`
- Path: `source/` (layout preserved under each version directory)

The files are exact upstream copies (including their `$id`). `validate_ucp.py`
loads them into a `referencing` registry keyed by file path and strips `$id` at
load time, because the upstream `$ref`s are written to resolve by **file path**
relative to `source/`, not by `$id`.

## Updating

To refresh for a new spec version, fetch `discovery/profile_schema.json` and
follow its `$ref`s transitively (relative to `source/`) into a new
`refs/ucp-schema/<version>/` directory, then bump `SCHEMA_VERSION` in
`skills/ucp-validate/scripts/validate_ucp.py`.

These are not a substitute for the official `ucp-schema` CLI or the conformance
suite for full runtime behavior; they cover structural profile validation.
