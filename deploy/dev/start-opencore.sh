#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# OpenCore-only dev start: forces commercial off (no need to remember the env var).
# Same usage as start.sh:
#   bash deploy/dev/start-opencore.sh demo-sg
set -euo pipefail
export FML_COMMERCIAL=0
exec "$(cd "$(dirname "$0")" && pwd)/start.sh" "$@"
