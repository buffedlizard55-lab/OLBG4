#!/usr/bin/env bash
# Board SA (session 696c1a7c) — rebuild every published artefact from the capture.
#
# The capture itself needs the network and is produced by
# `.github/workflows/sa-696c1a7c.yml`; everything below reads the committed bytes,
# so this script is deterministic and safe for CI to re-run.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "1/6 official facts (all captured runs, newest first)"
python3 scripts/session-696c1a7c/official.py

echo "2/6 OLBG listing"
python3 scripts/session-696c1a7c/parse_listings.py

echo "3/6 originated lines"
python3 scripts/session-696c1a7c/originate.py

echo "4/6 picks"
python3 scripts/session-696c1a7c/picks.py

echo "5/6 written predictions + individual sports"
python3 scripts/session-696c1a7c/individual.py
python3 scripts/session-696c1a7c/predict.py

echo "6/6 site and checks"
python3 scripts/session-696c1a7c/build_site.py
python3 scripts/session-696c1a7c/verify.py
