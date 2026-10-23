#!/usr/bin/env bash
# Board AH (arena/b2c7308d-olbg4) — full build: originate → review → site → verify.
# Requires capture data under data/session-b2c7308d/capture/<stamp>/ (fetch.py provides it).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

python3 -c "import pypdf" 2>/dev/null || \
  python3 -m pip install --quiet --break-system-packages pypdf || \
  python3 -m pip install --quiet pypdf

python3 "$HERE/originate_desk.py"
python3 "$HERE/review.py"
python3 "$HERE/build_site.py"
python3 "$HERE/verify.py"
echo "[board-ah] build_all: OK"
