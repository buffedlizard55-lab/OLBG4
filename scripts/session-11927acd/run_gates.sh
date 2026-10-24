#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ -z "${RI_GENERATED_UTC:-}" && -f data/session-11927acd/meta.json ]]; then
  export RI_GENERATED_UTC="$(python3 -c 'import json; print(json.load(open("data/session-11927acd/meta.json"))["generated_utc"])')"
fi
python3 scripts/session-11927acd/audit.py
python3 scripts/session-11927acd/build_data.py
python3 scripts/session-11927acd/build_site.py
python3 scripts/session-11927acd/verify.py
