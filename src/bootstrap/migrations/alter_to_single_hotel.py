# SPDX-License-Identifier: Apache-2.0
"""单体酒店迁移：去掉租户表，补齐用户密码，保留第一家酒店。"""

from sqlalchemy import inspect, text

from database import SessionLocal
from infra.auth_local import DEFAULT_HOTEL_ID, hash_password
from models import Hotel, Role, User


def ensure_single_hotel_schema(engine):
    """旧库兼容：删除租户表、users 加 password_hash。"""
    insp = inspect(engine)
    tables = set(insp.get_table_names())

    # ⚠️ 关键修复（连接池自死锁）：
    # inspect(engine) 每次反射会从连接池另开一条连接。若把 get_columns 放在
    # engine.begin() 写事务内部，写连接已持有 users/hotels 的 ACCESS EXCLUSIVE 锁
    # （DROP ... CASCADE 删外键所致，事务未提交），反射连接再去读这些表的元数据
    # 就要等 ACCESS SHARE 锁 → 被写连接自己堵死 → 永久挂起。
    # 因此所有只读反射必须在打开写事务【之前】完成，事务内只跑纯 DDL。
    users_cols = {c["name"] for c in insp.get_columns("users")} if "users" in tables else set()
    hotels_cols = {c["name"] for c in insp.get_columns("hotels")} if "hotels" in tables else set()

    with engine.begin() as conn:
        # 锁/语句超时保护：DROP ... CASCADE 删外键需 ACCESS EXCLUSIVE 锁，
        # 若被其它连接/事务持有会无限等待。这里强制 30s 锁超时、60s 语句超时，
        # 失败即报错而非永久挂起。
        conn.execute(text("SET LOCAL lock_timeout = '30s'"))
        conn.execute(text("SET LOCAL statement_timeout = '60s'"))

        # 旧版多租户库兼容：单酒店模型不再需要租户表。
        # PostgreSQL 不允许在有外键依赖时直接 DROP 表，必须 CASCADE；
        # CASCADE 仅级联删除"依赖 tenants 的对象"（hotels/users 上的外键约束），
        # 不会删除被引用表本身，hotels/users 的数据与表结构均保留。
        if "tenant_credentials" in tables:
            print("[single_hotel] drop tenant_credentials CASCADE")
            conn.execute(text("DROP TABLE IF EXISTS tenant_credentials CASCADE"))
        if "tenants" in tables:
            print("[single_hotel] drop tenants CASCADE")
            conn.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))

        if "users" in tables:
            print("[single_hotel] patch users")
            cols = users_cols
            if "password_hash" not in cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(128)"))
            # 单酒店模型不再需要 tenant_id 列：PostgreSQL 支持 DROP COLUMN；
            # 此处 try/except 仅为兼容性兜底（与原逻辑一致）。
            if "tenant_id" in cols:
                try:
                    conn.execute(text("ALTER TABLE users DROP COLUMN tenant_id"))
                except Exception:
                    pass

        if "hotels" in tables:
            print("[single_hotel] patch hotels")
            cols = hotels_cols
            if "tenant_id" in cols:
                try:
                    conn.execute(text("ALTER TABLE hotels DROP COLUMN tenant_id"))
                except Exception:
                    pass
    print("[single_hotel] done")


def ensure_local_users(db=None):
    """确保默认本地账号存在（幂等）。"""
    own = db is None
    if own:
        db = SessionLocal()
    try:
        hotel = db.query(Hotel).order_by(Hotel.id).first()
        if not hotel:
            return {"users_added": 0}
        from seed.locale_pack import get_pack

        pack = get_pack()
        defaults = list(
            getattr(pack, "LOCAL_USERS", None)
            or [
                ("admin", "admin123", "admin", "系统管理员"),
                ("gm", "gm123", "gm", "店长"),
                ("revenue", "rm123", "rm", "收益经理"),
                ("front", "front123", "fd", "前台"),
            ]
        )
        roles = {r.code: r for r in db.query(Role).all()}
        added = 0
        for username, password, role_code, full_name in defaults:
            u = db.query(User).filter_by(username=username).first()
            if not u:
                role = roles.get(role_code)
                u = User(
                    hotel_id=hotel.id,
                    role_id=role.id if role else None,
                    username=username,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    is_active=True,
                )
                db.add(u)
                added += 1
            else:
                u.full_name = full_name
                if not u.password_hash:
                    u.password_hash = hash_password(password)
                if not u.hotel_id:
                    u.hotel_id = hotel.id
                role = roles.get(role_code)
                if role:
                    u.role_id = role.id
                u.is_active = True
        db.commit()
        return {"users_added": added, "hotel_id": hotel.id}
    finally:
        if own:
            db.close()


def prune_extra_hotels(db=None):
    """仅保留第一家酒店（库从多店迁单店时用）。"""
    own = db is None
    if own:
        db = SessionLocal()
    try:
        hotels = db.query(Hotel).order_by(Hotel.id).all()
        if len(hotels) <= 1:
            return {"removed": 0}
        keep = hotels[0]
        removed = 0
        for h in hotels[1:]:
            db.delete(h)
            removed += 1
        db.commit()
        return {"removed": removed, "kept_hotel_id": keep.id}
    finally:
        if own:
            db.close()
