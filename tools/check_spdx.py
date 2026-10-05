# SPDX-License-Identifier: Apache-2.0
"""Require SPDX-License-Identifier on first-party source files.

OpenCore (default): Apache-2.0
src/commercial/: BUSL-1.1 (JSON may use "spdxLicenseIdentifier")

Usage:
  python tools/check_spdx.py
  python tools/check_spdx.py --fix
  python tools/check_spdx.py --commercial-only
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    "tmp",
    ".cache",
    "coverage",
}
CODE_SUFFIX = {".py", ".vue", ".ts", ".js", ".mjs", ".cjs", ".css", ".sql", ".sh", ".html"}
JSON_SUFFIX = {".json"}
NEEDLE = re.compile(r"SPDX-License-Identifier:\s*(\S+)")
JSON_NEEDLE = re.compile(r'"spdxLicenseIdentifier"\s*:\s*"([^"]+)"')


def is_skipped(path: Path) -> bool:
    return any(p in SKIP_DIRS for p in path.parts)


def expected_license(rel: Path) -> str:
    parts = rel.as_posix().split("/")
    if "commercial" in parts and parts[0] == "src":
        return "BUSL-1.1"
    return "Apache-2.0"


def in_scope(rel: Path, commercial_only: bool) -> bool:
    posix = rel.as_posix()
    if commercial_only:
        return posix.startswith("src/commercial/")
    if posix.startswith("src/") or posix.startswith("tools/"):
        return True
    if posix.startswith("frontend/") and not posix.startswith("frontend/node_modules/"):
        return True
    if posix.startswith("deploy/") or posix.startswith("db/"):
        return True
    return False


def found_license(text: str, suffix: str) -> str | None:
    head_lines = text.splitlines()[:24]
    head = "\n".join(head_lines)
    if suffix == ".json":
        m = JSON_NEEDLE.search(head)
        if m:
            return m.group(1)
        m = NEEDLE.search(head)
        if m:
            return m.group(1)
        return None
    for raw in head_lines:
        s = raw.strip()
        if s.startswith("#!"):
            continue
        if suffix == ".py" and re.match(r"^#.*coding[:=]", s):
            continue
        if s.startswith("<!--") and s.endswith("-->"):
            s = s[4:-3].strip()
        elif s.startswith("/*") and s.endswith("*/"):
            s = s[2:-2].strip()
        elif s.startswith("//"):
            s = s[2:].strip()
        elif s.startswith("--"):
            s = s[2:].strip()
        elif s.startswith("#"):
            s = s[1:].strip()
        else:
            continue
        if s.startswith("SPDX-License-Identifier:"):
            return s.split(":", 1)[1].strip().split()[0]
    return None


def comment_line(suffix: str, license_id: str) -> str:
    tag = f"SPDX-License-Identifier: {license_id}"
    if suffix in {".py", ".sh"}:
        return f"# {tag}\n"
    if suffix in {".ts", ".js", ".mjs", ".cjs"}:
        return f"// {tag}\n"
    if suffix == ".css":
        return f"/* {tag} */\n"
    if suffix in {".vue", ".html"}:
        return f"<!-- {tag} -->\n"
    if suffix == ".sql":
        return f"-- {tag}\n"
    raise ValueError(suffix)


def insert_header(text: str, suffix: str, license_id: str) -> str:
    line = comment_line(suffix, license_id)
    if text.startswith("\ufeff"):
        rest = text[1:]
        return "\ufeff" + insert_header(rest, suffix, license_id)
    lines = text.splitlines(keepends=True)
    i = 0
    if lines and lines[0].startswith("#!"):
        i = 1
    if suffix == ".py" and i < len(lines) and re.match(r"^#.*coding[:=]", lines[i]):
        i += 1
    if suffix == ".html" and lines and lines[0].lstrip().lower().startswith("<!doctype"):
        i = max(i, 1)
    return "".join(lines[:i]) + line + "".join(lines[i:])


def iter_files(commercial_only: bool) -> list[Path]:
    roots = (
        [ROOT / "src" / "commercial"]
        if commercial_only
        else [
            ROOT / "src",
            ROOT / "tools",
            ROOT / "frontend",
            ROOT / "deploy",
            ROOT / "db",
        ]
    )
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or is_skipped(path):
                continue
            rel = path.relative_to(ROOT)
            if not in_scope(rel, commercial_only):
                continue
            if path.suffix not in CODE_SUFFIX | JSON_SUFFIX:
                continue
            if path.suffix in JSON_SUFFIX and not rel.as_posix().startswith("src/commercial/"):
                continue
            out.append(path)
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="Insert missing SPDX headers")
    ap.add_argument("--commercial-only", action="store_true")
    args = ap.parse_args()

    missing: list[str] = []
    wrong: list[str] = []
    fixed = 0
    for path in iter_files(args.commercial_only):
        rel = path.relative_to(ROOT)
        want = expected_license(rel)
        text = path.read_text(encoding="utf-8")
        got = found_license(text, path.suffix)
        if got == want:
            continue
        if got and got != want:
            wrong.append(f"{rel.as_posix()}: have {got}, want {want}")
            continue
        if path.suffix == ".json":
            missing.append(rel.as_posix())
            continue
        if args.fix:
            path.write_text(insert_header(text, path.suffix, want), encoding="utf-8", newline="")
            fixed += 1
        else:
            missing.append(rel.as_posix())

    if wrong:
        print("SPDX license mismatch:")
        print("\n".join(wrong))
    if missing:
        print("missing SPDX-License-Identifier:")
        print("\n".join(missing))
    if wrong or missing:
        if args.fix and missing:
            print("(JSON cannot auto-insert; add spdxLicenseIdentifier)")
        return 1
    extra = f", inserted {fixed}" if args.fix else ""
    scope = "commercial" if args.commercial_only else "source"
    print(f"{scope} SPDX ok{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
