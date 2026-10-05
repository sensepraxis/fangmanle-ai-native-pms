# SPDX-License-Identifier: Apache-2.0
"""企微消息加解密（客户联系回调）。使用 cryptography 库。"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
from xml.etree import ElementTree as ET

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class WecomCryptoError(Exception):
    pass


def _pkcs7_pad(data: bytes, block: int = 32) -> bytes:
    amount = block - (len(data) % block)
    return data + bytes([amount] * amount)


def _pkcs7_unpad(data: bytes, block: int = 32) -> bytes:
    amount = data[-1]
    if amount < 1 or amount > block:
        raise WecomCryptoError("pkcs7 填充非法")
    return data[:-amount]


class WecomMsgCrypt:
    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.token = token or ""
        self.corp_id = corp_id or ""
        key = (encoding_aes_key or "").strip()
        if len(key) != 43:
            raise WecomCryptoError("EncodingAESKey 长度应为 43")
        self.aes_key = base64.b64decode(key + "=")

    def _sha1(self, *parts: str) -> str:
        s = "".join(sorted(parts))
        return hashlib.sha1(s.encode("utf-8")).hexdigest()

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        sig = self._sha1(self.token, timestamp, nonce, echostr)
        if sig != msg_signature:
            raise WecomCryptoError("URL 验签失败")
        return self.decrypt(echostr)

    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, post_data: str) -> str:
        root = ET.fromstring(post_data)
        encrypt = (root.findtext("Encrypt") or "").strip()
        sig = self._sha1(self.token, timestamp, nonce, encrypt)
        if sig != msg_signature:
            raise WecomCryptoError("消息验签失败")
        return self.decrypt(encrypt)

    def decrypt(self, cipher_text: str) -> str:
        decryptor = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_key[:16])).decryptor()
        plain = _pkcs7_unpad(decryptor.update(base64.b64decode(cipher_text)) + decryptor.finalize())
        msg_len = socket.ntohl(struct.unpack("I", plain[16:20])[0])
        return plain[20 : 20 + msg_len].decode("utf-8")

    def encrypt_reply(self, reply: str, nonce: str, timestamp: str) -> str:
        random16 = os.urandom(16)
        msg = reply.encode("utf-8")
        corp = self.corp_id.encode("utf-8")
        raw = random16 + struct.pack("I", socket.htonl(len(msg))) + msg + corp
        encryptor = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_key[:16])).encryptor()
        encrypt = base64.b64encode(encryptor.update(_pkcs7_pad(raw)) + encryptor.finalize()).decode("utf-8")
        sig = self._sha1(self.token, timestamp, nonce, encrypt)
        return (
            "<xml>"
            f"<Encrypt><![CDATA[{encrypt}]]></Encrypt>"
            f"<MsgSignature><![CDATA[{sig}]]></MsgSignature>"
            f"<TimeStamp>{timestamp}</TimeStamp>"
            f"<Nonce><![CDATA[{nonce}]]></Nonce>"
            "</xml>"
        )


def parse_event_xml(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    return {child.tag: (child.text or "") for child in root}
