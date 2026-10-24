#!/usr/bin/env python3
"""Board CA — one command to rebuild the whole desk and gate it.

    python3 scripts/session-e9770274/run.py            # rebuild from the newest committed capture
    python3 scripts/session-e9770274/run.py --capture  # also re-fetch (needs open egress: run in Actions)

Steps: read OLBG board -> originate lines -> write predictions -> review the repo -> meta (sources/flags)
-> build the site -> verify. Exits non-zero if the gate fails, so CI can refuse to publish.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    ("reverse-engineering the OLBG board", "re_olbg.py"),
    ("originating our own lines", "originate.py"),
    ("writing/validating predictions", "predictions.py"),
    ("reviewing the repository", "review_repo.py"),
    ("building sources + flags", "make_meta.py"),
    ("building the site", "build_site.py"),
    ("verification gate", "verify.py"),
]


def main() -> int:
    if "--capture" in sys.argv:
        print("== fetching live sources ==", flush=True)
        r = subprocess.run([sys.executable, str(HERE / "fetch.py")])
        if r.returncode:
            print("capture failed", file=sys.stderr)
            return r.returncode
    for label, script in STEPS:
        print(f"== {label} ==", flush=True)
        r = subprocess.run([sys.executable, str(HERE / script)])
        if r.returncode:
            print(f"FAILED at {script}", file=sys.stderr)
            return r.returncode
    print("desk rebuilt and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
