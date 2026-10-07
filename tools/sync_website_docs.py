# SPDX-License-Identifier: Apache-2.0
"""Copy root canonical docs into ``website/`` for MkDocs.

Edit INSTALL.md / ARCHITECTURE.md / FAQ.md at the repo root, then run:

    python tools/sync_website_docs.py

CI runs this before ``mkdocs build``. Relative links are rewritten to GitHub
blob URLs so they still work on Pages.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
REPO = "https://github.com/sensepraxis/fangmanle-ai-native-pms"
BLOB = f"{REPO}/blob/main"

# (source relative to ROOT, dest under website/, page title for banner)
PAGES = (
    ("INSTALL.md", "quick-start.md", "INSTALL.md"),
    ("ARCHITECTURE.md", "architecture.md", "ARCHITECTURE.md"),
    ("FAQ.md", "faq.md", "FAQ.md"),
)

# [text](path) where path is relative in-repo (not http/mailto/#)
_REL_LINK = re.compile(
    r"\[([^\]]+)\]\((?!https?://|mailto:|#|/)([^)]+)\)",
)


def _rewrite_links(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        label, target = m.group(1), m.group(2)
        # drop optional title in "path \"title\""
        path = target.split()[0].strip("\"'")
        if path.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        # normalize ./foo
        path = path[2:] if path.startswith("./") else path
        return f"[{label}]({BLOB}/{path})"

    return _REL_LINK.sub(repl, text)


def _banner(canonical: str) -> str:
    return (
        f"> Canonical source in the repository: "
        f"[`{canonical}`]({BLOB}/{canonical}). "
        f"Edit that file and re-run `python tools/sync_website_docs.py` "
        f"(CI does this automatically).\n\n"
    )


def main() -> int:
    WEBSITE.mkdir(parents=True, exist_ok=True)
    for src_name, dest_name, canonical in PAGES:
        src = ROOT / src_name
        if not src.is_file():
            raise SystemExit(f"missing {src}")
        body = src.read_text(encoding="utf-8")
        # Strip leading H1 — Material already shows the nav title; keep content.
        body = re.sub(r"^# .+\n+", "", body, count=1)
        out = _banner(canonical) + _rewrite_links(body)
        dest = WEBSITE / dest_name
        dest.write_text(out, encoding="utf-8", newline="\n")
        print(f"wrote {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
