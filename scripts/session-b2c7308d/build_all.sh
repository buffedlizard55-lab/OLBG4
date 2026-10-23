#!/usr/bin/env bash
# Board AH (b2c7308d) — full deterministic rebuild + verification gate.
set -euo pipefail
cd "$(dirname "$0")/../../.."
python3 -c "import pypdf" 2>/dev/null || pip install -q pypdf || pip install -q --break-system-packages pypdf
python3 scripts/session-b2c7308d/originate_desk.py
python3 scripts/session-b2c7308d/review.py
python3 scripts/session-b2c7308d/build_site.py
python3 scripts/session-b2c7308d/verify.py
echo "board-ah build_all: OK"
