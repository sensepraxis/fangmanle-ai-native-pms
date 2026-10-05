# SPDX-License-Identifier: Apache-2.0
"""测试种子数据生成（被 conftest.py 调用）。

包含：
  - SEED_USERS：标准 RBAC 账号 + 双审账号
  - HOTEL_ID：测试用酒店 id
  - _seed_core / _seed_corp / _seed_rooms_supplies_and_ops：种子数据函数
  - _activate_dual_review：强制激活双审账号
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import sessionmaker

from bootstrap.ensure_ar_ap import ensure_ar_ap_schema
from bootstrap.ensure_finance_float_carry import bootstrap_finance_float_carry
from bootstrap.ensure_finance_params_ext import bootstrap_finance_params_ext
from bootstrap.ensure_mkt_member_v2 import ensure_member_system_schema, seed_member_system

# 这些 import 在 conftest.py 已加载，_seed_data.py 通过 relative import 拿
from database import SessionLocal, engine
from infra.auth_local import hash_password
from infra.rbac_service import ensure_system_roles
from models import Base, CorpAccount, Hotel, Order, Room, RoomType, ServiceRequest, Supply, TagDefinition, User

HOTEL_ID = 1

SEED_USERS = [
    ("admin", "admin123", "admin", "系统管理员"),
    ("gm", "gm123", "gm", "店长"),
    ("revenue", "rm123", "rm", "收益经理"),
    ("front", "front123", "fd", "前台"),
    ("finance", "finance123", "gm", "财务(双审)"),
    ("manager", "manager123", "gm", "店长(双审)"),
]


def _seed_core(db) -> None:
    """酒店 + RBAC 角色 + 账号（get-or-create，幂等）。"""
    hotel = db.get(Hotel, HOTEL_ID)
    if hotel is None:
        hotel = Hotel(
            id=HOTEL_ID,
            code="LOCAL",
            name="测试本店",
            timezone="Asia/Shanghai",
            currency="CNY",
            star_rating=4,
            is_active=True,
        )
        db.add(hotel)
        db.flush()
    roles = ensure_system_roles(db)
    for username, password, role_code, full_name in SEED_USERS:
        role = roles.get(role_code)
        u = db.query(User).filter_by(username=username).first()
        if u is None:
            db.add(
                User(
                    hotel_id=HOTEL_ID,
                    role_id=role.id if role else None,
                    username=username,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    is_active=True,
                )
            )
        else:
            u.password_hash = hash_password(password)
            u.hotel_id = HOTEL_ID
            u.role_id = role.id if role else u.role_id
            u.is_active = True
    db.commit()


def _seed_corp(db) -> None:
    """ar_ap 用例需要至少一个激活协议客户（授信校验）。"""
    from models import CorpAccount

    if not db.query(CorpAccount).filter_by(hotel_id=HOTEL_ID, status="active").first():
        db.add(
            CorpAccount(
                hotel_id=HOTEL_ID,
                code="TESTCORP",
                name="测试协议客户",
                credit_limit=100000,
                credit_used=0,
                status="active",
            )
        )
        db.commit()


def _seed_rooms_supplies_and_ops(db) -> None:
    """班次交接「实物盘库 / 客情 / 待办」所需的最小运营数据。

    - 房型 + 房间：房间数驱动「万能房卡」应有数（min(4, 房间数 // 30)），
      60 间 → 2 张，使 HO-14 / TK-09 的实物差异拦截能跑出真实断言。
    - 物资库存：supplies.current_stock 直接作为交班实物应有盘点数，
      供 HO-10 对齐校验、HO-14 / TK-09 差异拦截使用。
    - 一条「今日即将到店」订单 → 接班客情「即将到店」，使 ST-06 的客情未确认拦截生效。
    - 一条在办客需工单 → 接班「待办」与客情，使 ST-06 的待办未承接拦截生效。
    """
    rt = db.query(RoomType).filter_by(hotel_id=HOTEL_ID, code="STD").first()
    if rt is None:
        rt = RoomType(hotel_id=HOTEL_ID, code="STD", name="标准大床房", capacity=2, base_price=399.0, is_active=True)
        db.add(rt)
        db.flush()
    if db.query(Room).filter_by(hotel_id=HOTEL_ID).count() < 60:
        for i in range(1, 61):
            db.add(
                Room(
                    hotel_id=HOTEL_ID,
                    room_type_id=rt.id,
                    room_no=f"{i:03d}",
                    floor=(i - 1) // 20 + 1,
                    status="vacant",
                    physical_status="normal",
                )
            )
        db.flush()
    for sku, name, unit, stock, safety in (("TOWEL", "客房毛巾", "条", 120, 30), ("WATER", "瓶装矿泉水", "瓶", 80, 20)):
        if not db.query(Supply).filter_by(hotel_id=HOTEL_ID, sku=sku).first():
            db.add(
                Supply(
                    hotel_id=HOTEL_ID,
                    category_id=None,
                    sku=sku,
                    name=name,
                    unit=unit,
                    current_stock=stock,
                    safety_stock=safety,
                )
            )
    today = date.today()
    if not db.query(Order).filter_by(hotel_id=HOTEL_ID, order_no="TEST-INBOUND-001").first():
        db.add(
            Order(
                hotel_id=HOTEL_ID,
                order_no="TEST-INBOUND-001",
                room_type_id=rt.id,
                order_type=1,
                check_in=today,
                check_out=today + timedelta(days=1),
                nights=1,
                rooms=1,
                adults=1,
                status="confirmed",
                payment_status="unpaid",
                arrival_time="14:00",
                note="自动化测试：VIP 续住客，请提前备好连通房",
            )
        )
    if not db.query(ServiceRequest).filter_by(hotel_id=HOTEL_ID, content="自动化测试客需-补充布草").first():
        db.add(ServiceRequest(hotel_id=HOTEL_ID, content="自动化测试客需-补充布草", priority=3, status="open"))
    db.commit()


def _activate_dual_review(db) -> None:
    """双审账号：ensure_rbac_users（被备用金引导流程调用）会把 finance 标记为停用
    （遗留账户映射），但「财务 + 店长」双授权备用金流程需要 finance 账号可用。
    这里强制 finance / manager 为激活态，作为测试库基线。"""
    for uname in ("finance", "manager"):
        u = db.query(User).filter_by(username=uname).first()
        if u:
            u.is_active = True
    db.commit()


def _bootstrap_demo_data(engine) -> None:
    """在指定 engine 上建表 + 灌最小演示数据。

    复用于：
    - pytest_configure（session-scope，兜底）
    - fresh_db fixture（每个 test 重灌）
    """
    Base.metadata.create_all(engine)
    ensure_ar_ap_schema(engine)
    db = sessionmaker(bind=engine)()
    try:
        _seed_core(db)
        bootstrap_finance_float_carry(engine, HOTEL_ID)
        bootstrap_finance_params_ext(engine, HOTEL_ID)
        ensure_member_system_schema(engine)
        seed_member_system(db, HOTEL_ID)
        _seed_rooms_supplies_and_ops(db)
        _seed_corp(db)
        _activate_dual_review(db)
    finally:
        db.close()
