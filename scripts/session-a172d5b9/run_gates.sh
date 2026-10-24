#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
CAPTURE="${1:-}"
if [[ -z "$CAPTURE" ]]; then
  CAPTURE=$(find data/session-a172d5b9/capture -mindepth 1 -maxdepth 1 -type d | sort | tail -1)
fi
export A172_CAPTURE_DIR="$CAPTURE"
python3 scripts/session-a172d5b9/build.py "$CAPTURE"
python3 scripts/session-a172d5b9/build_site.py
python3 scripts/session-a172d5b9/verify.py

digest() {
  { find data/session-a172d5b9 -maxdepth 1 -type f -name '*.json' -print0;
    find session-a172d5b9 -type f -print0; } | sort -z | xargs -0 sha256sum
}
digest > /tmp/a172-digest-first.txt
python3 scripts/session-a172d5b9/build.py "$CAPTURE" > /tmp/a172-rebuild.log
python3 scripts/session-a172d5b9/build_site.py > /tmp/a172-rebuild-site.log
digest > /tmp/a172-digest-second.txt
diff -u /tmp/a172-digest-first.txt /tmp/a172-digest-second.txt
python3 scripts/session-a172d5b9/verify.py
python3 scripts/audit_publication.py --check
git diff --check
printf 'PASS — deterministic rebuild and repository publication audit\n'
