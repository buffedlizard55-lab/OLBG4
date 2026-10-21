#!/usr/bin/env bash
# Rebuild every data file and the static site, then validate. Fails on any error.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/session-74f9613e/prepare_inputs.py
python3 scripts/session-74f9613e/model.py
python3 scripts/session-74f9613e/prepare_inventory.py
python3 scripts/session-74f9613e/build_site.py
python3 scripts/session-74f9613e/validate.py
