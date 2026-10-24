#!/usr/bin/env bash
# Rebuild every data file and the static site, then validate. Fails on any error.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/session-74f9613e/prepare_inputs.py
python3 scripts/session-74f9613e/model.py
python3 scripts/session-74f9613e/prepare_inventory.py
python3 scripts/session-74f9613e/build_site.py
python3 scripts/session-74f9613e/validate.py

# Board CA (b6643783) owns the root landing page and the desk/ dashboard. Render it from the
# committed Board CA data last, so this script reproduces exactly what is published.
python3 scripts/session-b6643783/build_site.py
python3 scripts/session-b6643783/verify.py
