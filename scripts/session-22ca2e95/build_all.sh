#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python3 scripts/session-22ca2e95/reconcile_olbg_and_audit.py
python3 scripts/session-22ca2e95/originate_desk.py
python3 scripts/session-22ca2e95/build_site.py
python3 scripts/session-22ca2e95/verify.py
