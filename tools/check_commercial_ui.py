# SPDX-License-Identifier: Apache-2.0
"""关商业包时，这些前端入口必须调 commercialEnabled()。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEEDLE = "commercialEnabled()"
REQUIRED = [
    "frontend/src/lib/branding.ts",
    "frontend/src/components/CommandPalette.vue",
    "frontend/src/components/ShiftAiDraftPanel.vue",
    "frontend/src/components/NarrativeInsightPanel.vue",
    "frontend/src/components/AnalyticsAiActions.vue",
    "frontend/src/components/HkAiPlanDrawer.vue",
    "frontend/src/components/FinanceAiPlanDrawer.vue",
    "frontend/src/views/c8-assets/asset-profile/AssetProfileAiNext.vue",
    "frontend/src/views/c5-frontdesk/order-attribution.vue",
    "frontend/src/views/c5-frontdesk/ai-new.vue",
    "frontend/src/views/c5-frontdesk/walk-in-quick-check-in.vue",
    "frontend/src/views/c6-housekeeping/staffing.vue",
    "frontend/src/views/c6-housekeeping/housekeeping.vue",
    "frontend/src/views/wecom/CareSidebar.vue",
    "frontend/src/views/acquisition/MktMembersPanel.vue",
    "frontend/src/views/acquisition/MktPointsPanel.vue",
    "frontend/src/views/c8-assets/loss-analysis-replacement-strategy.vue",
    "frontend/src/views/c9-finance/happy-house.vue",
    "frontend/src/views/c9-finance/revenue-forecast.vue",
]


def main() -> int:
    branding = ROOT / "frontend/src/lib/branding.ts"
    text = branding.read_text(encoding="utf-8")
    if "let _commercialEnabled = false" not in text:
        print("branding.ts 必须默认 _commercialEnabled = false")
        return 1
    missing: list[str] = []
    for rel in REQUIRED:
        path = ROOT / rel
        if not path.is_file():
            missing.append(f"{rel}: 文件不存在")
            continue
        body = path.read_text(encoding="utf-8")
        if NEEDLE not in body:
            missing.append(f"{rel}: 缺少 {NEEDLE}")
    if missing:
        print("commercialEnabled 覆盖清单未满足：")
        print("\n".join(missing))
        return 1
    print("commercial UI gate ok", "files=", len(REQUIRED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
