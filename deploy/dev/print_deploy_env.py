# SPDX-License-Identifier: Apache-2.0
"""Emit hotel YAML as cmd `set` or POSIX `export` statements."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from infra.hotel_config import load_hotel_doc, resolve_deploy, resolve_hotel_file  # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    posix = False
    if "--sh" in args:
        posix = True
        args = [a for a in args if a != "--sh"]
    hotel = args[0] if args and args[0] not in ("-", "") else None
    locale = args[1] if len(args) > 1 and args[1] not in ("-", "") else None
    d = resolve_deploy(pack=hotel, locale=locale)
    # resolve_deploy -> load_hotel_doc already resolved the file (and logged abs path on stderr)
    yaml_path = resolve_hotel_file()
    doc = load_hotel_doc()
    abs_yaml = str(yaml_path.resolve()) if yaml_path is not None else str(doc.get("_path") or "")
    assign = "export {k}={v}" if posix else "set {k}={v}"
    print(assign.format(k="FML_HOTEL", v=d.pack))
    print(assign.format(k="FML_PACKS", v=d.pack))
    print(assign.format(k="SEED_LOCALE", v=d.locale))
    print(assign.format(k="FML_DEFAULT_LOCALE", v=d.locale))
    # Quote for paths with spaces (POSIX); cmd set rarely needs quotes for drive paths.
    if posix:
        print(f'export FML_HOTEL_YAML="{abs_yaml}"')
    else:
        print(f"set FML_HOTEL_YAML={abs_yaml}")


if __name__ == "__main__":
    main()
