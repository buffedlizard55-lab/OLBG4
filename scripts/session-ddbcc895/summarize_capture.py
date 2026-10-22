#!/usr/bin/env python3
"""Print a one-screen summary of a Board AF capture manifest (run on the runner)."""
from __future__ import annotations

import json
import sys


def main() -> int:
    path = sys.argv[1]
    m = json.load(open(path, encoding="utf-8"))
    print(f"capture {m.get('started_utc')}: {m['http_200_nonempty_count']}/{m['target_count']} HTTP 200")
    for it in m["items"]:
        if it.get("status") != 200:
            print(f"  {it.get('status')} {it['id']} {it['url']} {str(it.get('error',''))[:70]}")
    missing = [it["id"] for it in m["items"] if it.get("status") == 200 and it.get("bytes", 0) == 0]
    if missing:
        print("  empty 200 bodies:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
