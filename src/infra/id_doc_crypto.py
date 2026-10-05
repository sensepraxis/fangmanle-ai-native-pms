# SPDX-License-Identifier: Apache-2.0
"""
敏感字段加密 / 脱敏 / 哈希（身份证号、手机号）。

合规约定：
- 密钥由酒店本地保管（data/hotel_keys/ 或环境变量），厂商交付物不含生产密钥
- 算法：默认 AES（Fernet）；若安装 gmssl 且 PMS_PII_ALG=sm4 则用国密 SM4
- 数据库只存 cipher + mask + hash；API/导出默认只返回 mask
- 身份证号只写入 pms_checkins，预订单不落证件明文
- 不落地身份证人像（仅 face_registered 标记，上报公安由酒店侧对接）
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

_DEMO_KEY_MATERIAL = "fangmanle-demo-id-doc-key-NOT-FOR-PROD"
# 仓库根：src/infra/id_doc_crypto.py -> src/infra/ -> src/ -> <repo root>
_ROOT = Path(__file__).resolve().parents[2]
# 默认 key 目录落到仓库根 data/hotel_keys/（被 .gitignore 的 data/** 排除）；
# 历史上曾经解析成 src/data/hotel_keys/，导致密钥被误 commit——已修正
_KEY_DIR = Path(os.environ.get("PMS_HOTEL_KEY_DIR") or (_ROOT / "data" / "hotel_keys"))


def key_dir() -> Path:
    _KEY_DIR.mkdir(parents=True, exist_ok=True)
    return _KEY_DIR


def hotel_key_path(hotel_id: int = 1) -> Path:
    return key_dir() / f"hotel_{int(hotel_id)}.key"


def ensure_hotel_key(hotel_id: int = 1) -> Path:
    """酒店本地生成/读取密钥文件；不写入仓库。"""
    path = hotel_key_path(hotel_id)
    if not path.exists():
        # 优先环境变量（酒店运维注入），否则本地生成随机密钥
        env = (os.environ.get("PMS_ID_DOC_KEY") or "").strip()
        material = env if env else secrets.token_urlsafe(48)
        path.write_text(material + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return path


def _key_material(hotel_id: Optional[int] = None) -> bytes:
    hid = int(hotel_id or os.environ.get("FML_DEFAULT_HOTEL_ID") or 1)
    # 1) 显式环境变量（酒店运维可注入，厂商镜像不含）
    env = (os.environ.get("PMS_ID_DOC_KEY") or "").strip()
    if env and env != _DEMO_KEY_MATERIAL:
        return env.encode("utf-8")
    # 2) 酒店本地密钥文件
    path = hotel_key_path(hid)
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if raw:
            return raw.encode("utf-8")
    # 3) Demo 回退（禁止生产）
    return _DEMO_KEY_MATERIAL.encode("utf-8")


def pii_algorithm() -> str:
    """返回实际使用的算法标签：sm4 | aes。"""
    want = (os.environ.get("PMS_PII_ALG") or "aes").strip().lower()
    if want == "sm4":
        try:
            from gmssl.sm4 import SM4_ENCRYPT, CryptSM4  # noqa: F401

            return "sm4"
        except Exception:
            return "aes"
    return "aes"


def _fernet(hotel_id: Optional[int] = None) -> Fernet:
    digest = hashlib.sha256(_key_material(hotel_id)).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _sm4_key(hotel_id: Optional[int] = None) -> bytes:
    return hashlib.sha256(_key_material(hotel_id)).digest()[:16]


def _encrypt_raw(plain: str, hotel_id: Optional[int] = None) -> str:
    alg = pii_algorithm()
    data = plain.encode("utf-8")
    if alg == "sm4":
        from gmssl.sm4 import SM4_ENCRYPT, CryptSM4

        crypt = CryptSM4()
        crypt.set_key(_sm4_key(hotel_id), SM4_ENCRYPT)
        # 简单 PKCS7 pad
        pad = 16 - (len(data) % 16)
        data = data + bytes([pad]) * pad
        cipher = crypt.crypt_ecb(data)
        return "v1:sm4:" + base64.urlsafe_b64encode(cipher).decode("ascii")
    token = _fernet(hotel_id).encrypt(data).decode("ascii")
    return "v1:aes:" + token


def _decrypt_raw(cipher: str, hotel_id: Optional[int] = None) -> str:
    if not cipher:
        return ""
    s = str(cipher)
    try:
        if s.startswith("v1:sm4:"):
            from gmssl.sm4 import SM4_DECRYPT, CryptSM4

            raw = base64.urlsafe_b64decode(s[7:].encode("ascii"))
            crypt = CryptSM4()
            crypt.set_key(_sm4_key(hotel_id), SM4_DECRYPT)
            data = crypt.crypt_ecb(raw)
            pad = data[-1]
            if 1 <= pad <= 16:
                data = data[:-pad]
            return data.decode("utf-8")
        if s.startswith("v1:aes:"):
            s = s[7:]
        # 兼容旧 Fernet 无前缀密文
        return _fernet(hotel_id).decrypt(s.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError, Exception):
        return ""


# ---------- 身份证 ----------


def normalize_id_doc(no: Optional[str]) -> str:
    if not no:
        return ""
    return re.sub(r"\s+", "", str(no)).upper()


def mask_id_doc(no: Optional[str]) -> str:
    s = normalize_id_doc(no)
    if not s:
        return ""
    if len(s) <= 8:
        return s[:2] + "*" * max(0, len(s) - 2)
    return f"{s[:4]}{'*' * (len(s) - 8)}{s[-4:]}"


def hash_id_doc(no: Optional[str], hotel_id: Optional[int] = None) -> str:
    s = normalize_id_doc(no)
    if not s:
        return ""
    pepper = _key_material(hotel_id)
    return hashlib.sha256(pepper + b"|" + s.encode("utf-8")).hexdigest()


def encrypt_id_doc(no: Optional[str], hotel_id: Optional[int] = None) -> str:
    s = normalize_id_doc(no)
    if not s:
        return ""
    return _encrypt_raw(s, hotel_id)


def decrypt_id_doc(cipher: Optional[str], hotel_id: Optional[int] = None) -> str:
    if not cipher:
        return ""
    return _decrypt_raw(str(cipher), hotel_id)


def pack_id_doc_fields(no: Optional[str], hotel_id: Optional[int] = None) -> dict:
    """写入 checkin 用的密文/掩码/哈希；无证号时全空。永不写入预订单。"""
    s = normalize_id_doc(no)
    if not s:
        return {"id_doc_cipher": None, "id_doc_mask": None, "id_doc_hash": None}
    return {
        "id_doc_cipher": encrypt_id_doc(s, hotel_id),
        "id_doc_mask": mask_id_doc(s),
        "id_doc_hash": hash_id_doc(s, hotel_id),
    }


# ---------- 手机号 ----------


def normalize_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    return re.sub(r"\D+", "", str(phone))


def mask_phone(phone: Optional[str]) -> str:
    s = normalize_phone(phone)
    if not s:
        return ""
    if len(s) < 7:
        return s[0] + "*" * max(0, len(s) - 1)
    return f"{s[:3]}****{s[-4:]}"


def hash_phone(phone: Optional[str], hotel_id: Optional[int] = None) -> str:
    s = normalize_phone(phone)
    if not s:
        return ""
    pepper = _key_material(hotel_id)
    return hashlib.sha256(pepper + b"|phone|" + s.encode("utf-8")).hexdigest()


def encrypt_phone(phone: Optional[str], hotel_id: Optional[int] = None) -> str:
    s = normalize_phone(phone)
    if not s:
        return ""
    return _encrypt_raw(s, hotel_id)


def decrypt_phone(cipher: Optional[str], hotel_id: Optional[int] = None) -> str:
    if not cipher:
        return ""
    return _decrypt_raw(str(cipher), hotel_id)


def pack_phone_fields(phone: Optional[str], hotel_id: Optional[int] = None) -> dict:
    s = normalize_phone(phone)
    if not s:
        return {"phone_cipher": None, "phone_mask": None, "phone_hash": None, "phone": None}
    return {
        "phone_cipher": encrypt_phone(s, hotel_id),
        "phone_mask": mask_phone(s),
        "phone_hash": hash_phone(s, hotel_id),
        # 列表/匹配默认只保留脱敏，明文不落地
        "phone": mask_phone(s),
    }


def key_status(hotel_id: int = 1) -> dict:
    path = hotel_key_path(hotel_id)
    env_set = bool((os.environ.get("PMS_ID_DOC_KEY") or "").strip())
    return {
        "algorithm": pii_algorithm(),
        "hotel_key_file": str(path),
        "hotel_key_exists": path.exists(),
        "env_key_configured": env_set and os.environ.get("PMS_ID_DOC_KEY") != _DEMO_KEY_MATERIAL,
        "vendor_holds_key": False,
        "note": "密钥由酒店本地保管；厂商交付物不含生产密钥。",
    }
