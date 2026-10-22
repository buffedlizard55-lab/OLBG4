#!/usr/bin/env bash
# Board AC: rebuild the desk, the review, the site, then verify everything.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/session-1695b749/ac_build.py
python3 scripts/session-1695b749/ac_review.py
python3 scripts/session-1695b749/ac_site.py
python3 scripts/session-1695b749/ac_verify.py
