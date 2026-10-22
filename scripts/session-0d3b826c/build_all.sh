#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="scripts/session-0d3b826c${PYTHONPATH:+:$PYTHONPATH}"
python3 scripts/session-0d3b826c/build.py
python3 scripts/session-0d3b826c/review.py
python3 scripts/session-0d3b826c/author.py
python3 scripts/session-0d3b826c/build.py
python3 scripts/session-0d3b826c/render.py
python3 scripts/session-0d3b826c/verify.py
