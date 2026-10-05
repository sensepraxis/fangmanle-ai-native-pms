# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""统计 Vue t() 频次，合并精翻词典，写回 locales/en.json 并 sync。

Usage:
  python tools/i18n_priority_translate.py
  python tools/i18n_priority_translate.py --top 50
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_catalog import CANONICAL, save_canonical, sync_mirrors  # noqa: E402

T_CALL = re.compile(r"""\bt\(\s*['"]([^'"]+)['"]""")

# 精翻白名单：壳 / 登录 / 订单 / 押金 / 通用（覆盖率优先于全量）
HAND: dict[str, str] = {
    # Login
    "让每一间房，": "Fill every room,",
    "都满起来": "every night",
    "AI 原生酒店 PMS —— 把入住、房态、收益与私域增长，交给一套会思考的系统。": (
        "AI-native hotel PMS — occupancy, rooms, revenue and private-domain growth in one thinking system."
    ),
    "私域获客": "Private-domain acquisition",
    "企微触达，沉淀复购": "WeCom reach, drive repeat stays",
    "AI 指导经营": "AI-guided operations",
    "数据洞察，辅助决策": "Insights that support decisions",
    "自动处理 Routine 事务": "Automate routine work",
    "智能定价": "Smart pricing",
    "动态收益最大化": "Maximize dynamic revenue",
    "我是小满 ◐": "I'm Xiaoman ◐",
    "你的 AI 店长助手，登录后即可调度。": "Your AI manager assistant — sign in to start.",
    "密码登录": "Password",
    "验证码登录": "SMS code",
    "账号 / 手机号": "Account / mobile",
    "请输入账号或注册手机号": "Account or registered mobile",
    "密码": "Password",
    "请输入密码": "Enter password",
    "记住我": "Remember me",
    "忘记密码？": "Forgot password?",
    "请联系系统管理员重置密码": "Contact an admin to reset your password",
    "手机号": "Mobile",
    "请输入手机号": "Enter mobile number",
    "短信验证码": "SMS code",
    "6 位验证码": "6-digit code",
    "登 录": "Sign in",
    "登录": "Sign in",
    "请输入正确的手机号": "Enter a valid mobile number",
    "验证码登录中，请使用密码登录": "SMS sign-in is not ready; use password",
    "短信验证码登录即将接入，请先使用密码登录": "SMS sign-in coming soon; use password for now",
    "登录失败：": "Sign-in failed: ",
    "欢迎，": "Welcome, ",
    "中文": "中文",
    # Shell / common phrases (msgid form)
    "经营总览": "Overview",
    "订单管理": "Orders",
    "房务与房态": "Rooms & Status",
    "客户会员": "Guests & Members",
    "数据洞察": "Analytics",
    "财务管理": "Finance",
    "私域运营": "Private Domain",
    "系统配置": "System",
    "保存": "Save",
    "取消": "Cancel",
    "确认": "Confirm",
    "删除": "Delete",
    "搜索": "Search",
    "加载中": "Loading",
    "加载中…": "Loading…",
    "加载中...": "Loading...",
    "退出登录": "Log out",
    "通知": "Notifications",
    "店长": "Manager",
    "已退出登录": "Signed out",
    "语言": "Language",
    "成功": "Success",
    "失败": "Failed",
    "重试": "Retry",
    "返回": "Back",
    "更多": "More",
    "全部": "All",
    "详情": "Details",
    "编辑": "Edit",
    "新建": "Create",
    "刷新": "Refresh",
    "导出": "Export",
    "设置": "Settings",
    "暂无数据": "No data",
    "用户名": "Username",
    "酒店": "Hotel",
    "欢迎回来": "Welcome back",
    "未登录或令牌失效": "Not signed in or token expired",
    "请求失败": "Request failed",
    "接口未生效（Method Not Allowed），请重启后端服务后再试": (
        "API not available (Method Not Allowed). Restart the backend and retry."
    ),
    "请先登录": "Please sign in",
    # Orders
    "前台取消": "Front desk cancel",
    "订单": "Order",
    "订单号": "Order no.",
    "房型": "Room type",
    "房号": "Room no.",
    "入住人": "Guest",
    "入住": "Check-in",
    "退房": "Check-out",
    "在住": "In-house",
    "已确认": "Confirmed",
    "待确认": "Pending",
    "已取消": "Cancelled",
    "已完成": "Completed",
    "预订": "Reservation",
    "入住日期": "Arrival",
    "离店日期": "Departure",
    "间夜": "Room nights",
    "渠道": "Channel",
    "金额": "Amount",
    "状态": "Status",
    "操作": "Actions",
    "筛选": "Filter",
    "今日到店": "Arrivals today",
    "今日离店": "Departures today",
    "待排房": "Pending assignment",
    "排房": "Assign room",
    "换房": "Change room",
    "续住": "Extend stay",
    "结账": "Checkout",
    "收银": "Cashiering",
    "客人": "Guest",
    "姓名": "Name",
    "备注": "Notes",
    "创建": "Create",
    "提交": "Submit",
    "关闭": "Close",
    "查看": "View",
    "复制": "Copy",
    "打印": "Print",
    "无": "None",
    "是": "Yes",
    "否": "No",
    "未知": "Unknown",
    # Deposit / finance
    "押金": "Deposit",
    "押金管理": "Deposit management",
    "收押": "Collect deposit",
    "扣押": "Capture",
    "释放": "Release",
    "在押": "On hold",
    "待收押": "Pending collect",
    "扣减中": "Partial capture",
    "失效": "Expired",
    "争议": "Disputed",
    "已释放": "Released",
    "全额扣减": "Fully captured",
    "银行卡预授权": "Card pre-auth",
    "微信押金": "WeChat deposit",
    "支付宝押金": "Alipay deposit",
    "现金": "Cash",
    "企业挂账": "Corporate AR",
    "微信支付": "WeChat Pay",
    "支付宝": "Alipay",
    "银行卡 / POS": "Card / POS",
    "银行转账": "Bank transfer",
    "协议挂账": "Corporate AR",
    "押金冲抵": "Deposit offset",
    "直付": "Direct pay",
    "OTA 预付": "OTA prepaid",
    "微信 POS": "WeChat POS",
    "支付宝 POS": "Alipay POS",
    "营收": "Revenue",
    "夜审": "Night audit",
    "对账": "Reconciliation",
    "开票": "Invoicing",
    "应收": "AR",
    "应付": "AP",
    "退款": "Refund",
    "调账": "Adjustment",
    "日报": "Daily report",
    "异常": "Exception",
    "汇总": "Summary",
    "今日": "Today",
    "本月": "This month",
    "对比": "Compare",
    # Rooms / HK
    "空房": "Vacant",
    "脏房": "Dirty",
    "净房": "Clean",
    "维修": "OOO",
    "清洁": "Cleaning",
    "派工": "Dispatch",
    "房务": "Housekeeping",
    "楼层": "Floor",
    "排班": "Staffing",
    # Channels
    "微信": "WeChat",
    "企微": "WeCom",
    "企业微信": "WeCom",
    "携程": "Ctrip",
    "美团": "Meituan",
    "飞猪": "Fliggy",
    "抖音": "Douyin",
    "小红书": "Xiaohongshu",
    "官网": "Official site",
    "散客": "Walk-in",
    "散客上门": "Walk-in",
    "协议客户": "Corporate",
    "直订": "Direct",
    "直销": "Direct",
    "会员": "Member",
    "协议": "Corporate",
    "系统": "System",
    "未知渠道": "Unknown channel",
    "本店私域": "On-property private domain",
    # Domains
    "AI 中台": "AI Core",
    "数据底座": "Data Platform",
    "收益管理": "Revenue",
    "风控预警": "Risk",
    "获客种草": "Acquisition",
    "口碑传播": "Reputation",
    "前台接待": "Front Desk",
    "客房服务": "Housekeeping",
    "物资耗材": "Supplies",
    "固定资产": "Assets",
    "财务中心": "Finance Center",
    "多形态多门店": "Multi-property",
    # Errors / domain
    "规则不存在": "Rule not found",
    "关联订单不存在": "Order not found",
    "押金单不存在": "Deposit not found",
    "交班记录不存在": "Handover not found",
    "券批次不存在": "Coupon batch not found",
    "非法状态": "Invalid state",
    "缺少 plan": "Missing plan",
    "请至少勾选一项再确认": "Select at least one item",
    "请填写规则名称": "Please enter a rule name",
    "请选择触发事件": "Please select a trigger event",
    "请至少选择一张券批次": "Select at least one coupon batch",
    "已归档不可生成 AI 草稿": "Archived; cannot generate AI draft",
    "已归档不可确认": "Archived; cannot confirm",
    "请至少勾选一项 AI 草稿": "Select at least one AI draft item",
    "请至少勾选一张操作单": "Select at least one action item",
    "状态 {status} 不允许事件 {event}": "Status {status} does not allow event {event}",
    "暂未查到相关数据": "No matching data",
    "查询完成": "Query complete",
    "语言跟随顶栏；已生成内容需重新生成": "Language follows the top bar; regenerate for new language",
    "生成 AI 草稿": "Generate AI draft",
    "AI确认执行": "Confirm AI actions",
    "重新生成": "Regenerate",
    "建议确认": "Suggested confirmations",
    "智能分析暂不可用，已给常规建议": "AI unavailable; showing rule-based suggestions",
    "暂无可执行安排": "No actionable items",
    "暂无 AI 建议项": "No AI suggestions",
}


def collect_freq() -> Counter[str]:
    c: Counter[str] = Counter()
    roots = [
        ROOT / "frontend" / "src" / "components",
        ROOT / "frontend" / "src" / "views",
    ]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.vue"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in T_CALL.finditer(text):
                key = m.group(1).strip()
                if key and not key.startswith("common.") and not key.startswith("nav."):
                    c[key] += 1
                elif key:
                    c[key] += 1
    return c


def sync_locales(en: dict, zh_src: Path | None = None) -> None:
    save_canonical("en.json", en)
    if zh_src and zh_src.exists() and zh_src.resolve() != (CANONICAL / "zh-CN.json").resolve():
        shutil.copy(zh_src, CANONICAL / "zh-CN.json")
    sync_mirrors()


def load_hand_packs() -> dict[str, str]:
    """Merge tools/_i18n_hand_*.json packs into HAND overrides."""
    out: dict[str, str] = dict(HAND)
    hand_files = sorted((ROOT / "tools").glob("_i18n_hand_*.json"))
    for p in hand_files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, str) and v.strip():
                    out[k] = v
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=80, help="print top-N untranslated")
    args = ap.parse_args()

    en_path = CANONICAL / "en.json"
    en = json.loads(en_path.read_text(encoding="utf-8"))
    phrases: dict[str, str] = dict(en.get("phrases") or {})

    hand = load_hand_packs()
    # Apply hand translations (overwrite same-as-zh)
    applied = 0
    for k, v in hand.items():
        if phrases.get(k) != v:
            applied += 1
        phrases[k] = v

    freq = collect_freq()
    # Ensure top frequent msgids exist in phrases (fallback zh until translated)
    for msgid, _n in freq.most_common(500):
        phrases.setdefault(msgid, hand.get(msgid, msgid))

    en["phrases"] = dict(sorted(phrases.items(), key=lambda x: x[0]))
    sync_locales(en, CANONICAL / "zh-CN.json")

    same = sum(1 for k, v in phrases.items() if k == v)
    hand_hit = sum(1 for k in hand if phrases.get(k) == hand[k])
    print(
        f"phrases={len(phrases)} same_as_zh={same} hand_keys={len(hand)} "
        f"hand_applied_changes={applied} hand_ok={hand_hit}"
    )
    untranslated = [(k, n) for k, n in freq.most_common(args.top * 3) if phrases.get(k, k) == k]
    print("--- top untranslated by freq ---")
    for k, n in untranslated[: args.top]:
        print(f"{n:4d}  {k}")


if __name__ == "__main__":
    main()
