#!/usr/bin/env bash
# Board ED (arena/ed4c358c-olbg4) — full deterministic rebuild.
# Requires the capture under data/session-ed4c358c/capture/<stamp>/ committed by .github/workflows/ed-4c358c.yml
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 -c "import bs4, pypdf" 2>/dev/null || \
  python3 -m pip install --quiet --break-system-packages beautifulsoup4 lxml pypdf || \
  python3 -m pip install --quiet beautifulsoup4 lxml pypdf
python3 "$HERE/re_olbg.py"
python3 "$HERE/originate.py"
python3 "$HERE/predictions.py"
python3 "$HERE/review.py"
python3 "$HERE/build_site.py"
python3 "$HERE/verify.py"
