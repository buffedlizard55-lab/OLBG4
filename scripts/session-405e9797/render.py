#!/usr/bin/env python3
"""Board AR — headless render capture for official pages that ship a client-side shell.

The plain HTTP fetcher (fetch.py) receives the un-rendered SvelteKit/Next/React shell for
several governing-body sites: the fixture table only exists after JavaScript runs. This
script drives headless Chromium (Playwright) on the Actions runner, waits for the network
to settle, and stores for each target:

    <id>.rendered.html.gz   full DOM after rendering
    <id>.innertext.txt.gz   document.body.innerText after rendering
    <id>.links.txt.gz       every anchor href + text after rendering

together with a SHA-256 manifest, so every subsequently parsed value can be traced to the
exact bytes that were captured. Nothing is typed in by hand.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36 OLBG4-BoardAR/1.0 (+https://github.com/buffedlizard55-lab/OLBG4)")


def gz(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as fh:
        fh.write(data)
    return buf.getvalue()


def main() -> int:
    targets_path, out_dir = sys.argv[1], sys.argv[2]
    targets = json.loads(Path(targets_path).read_text())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=UA, locale="en-GB",
                                  viewport={"width": 1440, "height": 1000})
        for idx, t in enumerate(targets, 1):
            tid, url = t["id"], t["url"]
            rec = {"id": tid, "url": url}
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                # give client-side tables one more beat, then scroll to trigger lazy blocks
                page.wait_for_timeout(1500)
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(1200)
                html = page.content()
                text = page.evaluate("() => document.body ? document.body.innerText : ''")
                links = page.evaluate(
                    "() => Array.from(document.querySelectorAll('a[href]'))"
                    ".map(a => (a.innerText||'').trim().slice(0,120) + '\\t' + a.href).join('\\n')")
                for suffix, payload in (("rendered.html", html.encode()),
                                        ("innertext.txt", (text or "").encode()),
                                        ("links.txt", (links or "").encode())):
                    fname = f"{tid}.{suffix}.gz"
                    (out / fname).write_bytes(gz(payload))
                    rec[suffix] = {"file": fname, "bytes": len(payload),
                                   "sha256": hashlib.sha256(payload).hexdigest()}
                rec["status"] = 200
                print(f"[{idx:03d}] OK   {tid} html={len(html)} text={len(text or '')} {url}", flush=True)
            except Exception as exc:
                rec["status"] = 0
                rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
                print(f"[{idx:03d}] ERR  {tid} {rec['error']} {url}", flush=True)
            finally:
                page.close()
            records.append(rec)
            time.sleep(0.4)
        ctx.close()
        browser.close()
    manifest = {
        "board": "AR", "session": "arena/405e9797-olbg4",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "targets": len(targets),
        "ok": sum(1 for r in records if r.get("status") == 200),
        "records": records,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(f"[board-ar] render finished {manifest['ok']}/{manifest['targets']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
