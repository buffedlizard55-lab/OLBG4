#!/usr/bin/env bash
# Board AB — rebuild every data file and the dashboard, then run the assertion gate.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/session-1695b749/build.py
python3 scripts/session-1695b749/listing.py
python3 scripts/session-1695b749/report.py
python3 scripts/session-1695b749/site.py
python3 scripts/session-1695b749/verify.py
