# SPDX-License-Identifier: Apache-2.0
"""Commercial Core SPDX — delegates to tools/check_spdx.py --commercial-only."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_CHECK = Path(__file__).resolve().parent / "check_spdx.py"


def main() -> int:
    return subprocess.call([sys.executable, str(_CHECK), "--commercial-only"])


if __name__ == "__main__":
    sys.exit(main())
