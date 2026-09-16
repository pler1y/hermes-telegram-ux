# Reproduce validation

Use the exact official baseline from `PUBLIC-API.md`. Keep Hermes core and dependencies outside the plugin checkout. A configured model and Telegram are not needed for automated checks.

```bash
git clone https://github.com/NousResearch/hermes-agent.git /tmp/catalog-core
git -C /tmp/catalog-core checkout --detach 3c3ab69abb9b08683b5eb15b4e2b8be1198c875f
(cd /tmp/catalog-core && uv sync --frozen --no-dev --no-install-project --python 3.11)
```

From the Catalog-safe source checkout:

```bash
CATALOG_PYTHON=/tmp/catalog-core/.venv/bin/python
export PYTHONPATH="$PWD:/tmp/catalog-core"
export HERMES_HOME="$(mktemp -d)"
"$CATALOG_PYTHON" -m unittest discover -s tests/unit -v
"$CATALOG_PYTHON" -m unittest discover -s tests/contract -v
"$CATALOG_PYTHON" scripts/check_boundary.py
"$CATALOG_PYTHON" -m hermes_cli.main plugins validate . --json
"$CATALOG_PYTHON" -m hermes_cli.main plugins doctor . --ci
"$CATALOG_PYTHON" scripts/check_native.py --core /tmp/catalog-core --ref HEAD
"$CATALOG_PYTHON" scripts/build_release.py --ref HEAD
```

The last two commands read committed Git objects; commit the reviewable candidate first. They never package uncommitted changes. Builds have fixed ZIP metadata, a reviewed allowlist, per-file hashes and a source SHA. `check_native.py` exercises both native Git installation at that SHA and the README's ZIP installation, the actual validators, disabled/enabled discovery, state cleanup, disable/remove, unrelated-config preservation and before/after hashes of all tracked Hermes files. Its deliberately undeclared hook must fail the official validator.

The native Git harness acknowledges scanner caution for its own reviewed local fixture using the documented `--force` flag. Scanning is not disabled; dangerous findings remain blocked. Official validation/doctor are mandatory, and tests must not be skipped to get a green run. Never copy this fixture trust flag into an unreviewed public installation command.

`tests/contract` uses the real current-core PluginManager and its bounded callback workers. Only the transport is synthetic. Runtime imports zero Hermes modules. The AST guard rejects external imports, private attributes, dynamic execution/rebinding and foreign-object mutation; it is an extra guard, not proof that code is safe. Human review still checks data flow and public API intent.

The GitHub workflow repeats these checks against the fixed baseline and current main on Python 3.11 and 3.12. Main is intentionally mutable for compatibility detection; installs remain pinned. Actual Telegram/model acceptance is separately recorded using `ACCEPTANCE.md`.
