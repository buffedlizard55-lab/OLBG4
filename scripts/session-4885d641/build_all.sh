#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

python3 scripts/session-4885d641/reconcile_and_audit.py
python3 scripts/session-4885d641/originate_desk.py
python3 scripts/session-4885d641/build_site.py
python3 scripts/session-4885d641/verify.py
