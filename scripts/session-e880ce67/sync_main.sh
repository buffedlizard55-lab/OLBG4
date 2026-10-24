#!/usr/bin/env bash
# Re-sync this branch with origin/main, keeping this board's own files and re-generating every
# shared artifact that main and this board both produce. Safe to run repeatedly.
set -euo pipefail
cd "$(dirname "$0")/../.."
git fetch origin --quiet
git merge origin/main --no-edit >/tmp/sync_merge.log 2>&1 || true
conflicts=$(git diff --name-only --diff-filter=U)
if [ -n "$conflicts" ]; then
  echo "resolving $(echo "$conflicts" | wc -l) generated conflicts in favour of main:"
  echo "$conflicts" | sed 's/^/  /'
  echo "$conflicts" | xargs -r git checkout --theirs --
  # this board's own scope always wins
  git checkout --ours -- COORDINATION.md 2>/dev/null || true
  echo "$conflicts" | xargs -r git add --
fi
# the nav pointer lives in another board's generator; re-apply if a merge dropped it
if ! grep -q 'session-e880ce67/index.html", "Board DS"' scripts/session-b6643783/build_site.py; then
  python3 - <<'PY'
p='scripts/session-b6643783/build_site.py'
s=open(p).read()
s=s.replace('''    ("desk/sources.html", "Sources"),\n]''','''    ("desk/sources.html", "Sources"),\n    # Board DS (arena/e880ce67-olbg4) — final-integration nav pointer. Logged in COORDINATION.md.\n    ("session-e880ce67/index.html", "Board DS"),\n]''')
open(p,'w').write(s)
PY
  echo "re-applied the Board DS nav pointer"
fi
# keep this board's log block even when main's copy of the log wins
if ! grep -q 'DS completion record — 2026-10-24 (session `e880ce67`' COORDINATION.md; then
  cat scripts/session-e880ce67/coordination_block.md >> COORDINATION.md
  echo "re-appended the Board DS log block"
fi
# regenerate everything both sides own
bash scripts/session-74f9613e/build_all.sh >/tmp/sync_build_all.log 2>&1
python3 tools/build_master.py >/dev/null
BOARD_OUT=board BOARD_EXT="../" python3 tools/build_master_site.py >/dev/null
python3 scripts/session-e880ce67/build_site.py
python3 scripts/session-e880ce67/verify.py | tail -1
BOARD_DIR=board python3 tools/verify_master.py | tail -1
git add -A
if ! git diff --cached --quiet; then
  git commit -q -m "Board DS: merge origin/main and regenerate shared artifacts"
  echo "committed"
fi
git push origin arena/e880ce67-olbg4
echo "synced at $(git log -1 --format='%h')"
