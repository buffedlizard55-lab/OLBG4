"""Local link + markup check for the Board S pages.

    python3 -m deskbot.linkcheck

Checks every href/src in the pages this session generated (the root landing page, the ten
desk pages and the two sport pages) against the filesystem, ignores external http(s)
links (they are official-source links and are listed on the Sources page instead), and
parses each page with html.parser to catch unclosed tags.
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PAGES = [ROOT / "index.html"] + sorted((ROOT / "desk").glob("*.html")) + sorted((ROOT / "desk" / "sports").glob("*.html"))

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr"}


class TagBalance(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"closing </{tag}> with an empty stack")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        else:
            if tag in self.stack:
                while self.stack and self.stack[-1] != tag:
                    self.errors.append(f"unclosed <{self.stack.pop()}> before </{tag}>")
                if self.stack:
                    self.stack.pop()
            else:
                self.errors.append(f"stray closing </{tag}>")


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.targets.append(v)


def main() -> int:
    bad: list[tuple[str, str]] = []
    checked = 0
    markup_errors: list[str] = []
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        lb = TagBalance()
        lb.feed(text)
        lb.close()
        if lb.stack:
            markup_errors.append(f"{page.relative_to(ROOT)}: unclosed {lb.stack}")
        markup_errors.extend(f"{page.relative_to(ROOT)}: {e}" for e in lb.errors)
        parser = Links()
        parser.feed(text)
        for target in parser.targets:
            if target.startswith(("#", "mailto:", "javascript:")) or target.startswith("http"):
                continue
            path_part = unquote(urlsplit(target).path)
            if not path_part:
                continue
            resolved = (page.parent / path_part).resolve()
            checked += 1
            if not resolved.exists():
                bad.append((str(page.relative_to(ROOT)), target))
    print(f"{len(PAGES)} pages · {checked} local targets checked · {len(bad)} broken · {len(markup_errors)} markup issues")
    for page, target in bad[:40]:
        print(f"  BROKEN {page} -> {target}")
    for m in markup_errors[:40]:
        print(f"  MARKUP {m}")
    return 1 if bad or markup_errors else 0


if __name__ == "__main__":
    sys.exit(main())
