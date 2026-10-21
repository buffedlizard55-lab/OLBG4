#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "=== [1/6] M1: Capture OLBG 28-Slot & Sub-Feed Taxonomy ==="
python3 scripts/session-ee9c2db4/capture_olbg_snapshot.py

echo "=== [2/6] M2 + M3: Originate 268 Events & 696 Complete Multi-Market Books ==="
python3 scripts/session-ee9c2db4/originate.py

echo "=== [3/6] M4: Attach & Verify 38 Bespoke High-Confidence Analyst Predictions ==="
python3 scripts/session-ee9c2db4/write_predictions.py

echo "=== [4/6] M5: Run 616-Row Line-by-Line Repository Audit ==="
python3 scripts/session-ee9c2db4/audit_repo.py

echo "=== [5/6] M6: Build 26 Static Executive Dashboard HTML Pages ==="
python3 scripts/session-ee9c2db4/build_site.py

echo "=== [6/6] M7: Validate All Schemas, Prose, Per-Row Links & Whole-Repo Links ==="
python3 scripts/session-ee9c2db4/validate.py
