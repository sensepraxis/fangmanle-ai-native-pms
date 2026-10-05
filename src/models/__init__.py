# SPDX-License-Identifier: Apache-2.0
"""房满乐 PMS —— SQLAlchemy 模型（按域拆分子包）。



原单一 models.py 已拆为以下子模块，对外接口保持不变：

``from models import Hotel, Order, GuestCoupon, ...`` 仍可用。



拆包目的：

- 单文件 150+ 模型过大，不利于 review 与按域维护

- 新人可按域（rooms / orders / finance / ...）独立探索 schema

- 未来要做 plugin / extension 时，新增域只需新增子文件



拆分清单：

- core       — Hotel / User / Role / Permission / RolePermission（基础 + RBAC）

- rooms      — RoomType / Room / RoomStatusLog / RoomNightInventory / Linen 等

- guests     — Guest / GuestAlias / OneId / Tag / CrmTask / Review

- orders     — Order / OrderItem / Reservation / Channel / Pms*

- hk         — HousekeepingTask / ServiceRequest / StaffShift*

- finance    — Finance* / ArAp / Deposit / Invoice / Recon / Tax / Ota / Corp / Refund / ShiftFloatAudit / NightAudit / ChannelCommission

- mkt        — Segment / Campaign / MktCoupon* / Acquisition / GuestCoupon / MktMember* / MktStoredValue / DemandForecast

- wecom      — WecomMsgTask / WecomBindTicket / WecomCallbackEvent / WxLanding*

- pricing    — PricingAssistantConfig / PricingRecommendation / PricingDecision / PricingEffect / RateStrategy / PriceSuggestion / RoomTypeBaseRate / Competitor* / ParityAlert / PaceSnapshot / EventCalendar / InventoryAllocation

- assets     — Asset* / Supply* / Linen / DamageTicket / Restock* / ShiftAssetCount

- analytics  — AiAskSession / AiReportInterpretation / ProfitInsight / RevenueAnomaly / RiskAlert / ShiftHandover* / LedgerEntry / AiCommand

- system     — AppSetting / Venue / VenueBooking / WebhookEventLog



**所有外键跨域引用通过 SQLAlchemy 字符串（"hotels.id" 等），无需 import 依赖。**

"""

from models import (
    _base,  # noqa: F401  触发模型注册到 Base.metadata
    analytics,  # noqa: F401  触发模型注册到 Base.metadata
    assets,  # noqa: F401  触发模型注册到 Base.metadata
    core,  # noqa: F401  触发模型注册到 Base.metadata
    finance,  # noqa: F401  触发模型注册到 Base.metadata
    guests,  # noqa: F401  触发模型注册到 Base.metadata
    hk,  # noqa: F401  触发模型注册到 Base.metadata
    mkt,  # noqa: F401  触发模型注册到 Base.metadata
    orders,  # noqa: F401  触发模型注册到 Base.metadata
    pricing,  # noqa: F401  触发模型注册到 Base.metadata
    rooms,  # noqa: F401  触发模型注册到 Base.metadata
    system,  # noqa: F401  触发模型注册到 Base.metadata
    wecom,  # noqa: F401  触发模型注册到 Base.metadata
)
from models.analytics import *  # noqa: F401,F403
from models.assets import *  # noqa: F401,F403

# Re-export 全部 ORM 类（保持 from models import Foo 兼容）
from models.core import *  # noqa: F401,F403
from models.finance import *  # noqa: F401,F403
from models.guests import *  # noqa: F401,F403
from models.hk import *  # noqa: F401,F403
from models.mkt import *  # noqa: F401,F403
from models.orders import *  # noqa: F401,F403
from models.pricing import *  # noqa: F401,F403
from models.rooms import *  # noqa: F401,F403
from models.system import *  # noqa: F401,F403
from models.wecom import *  # noqa: F401,F403
