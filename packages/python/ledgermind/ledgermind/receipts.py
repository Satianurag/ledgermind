"""Ed25519-signed resolution receipts."""

from __future__ import annotations

import base64
from typing import Any

import jcs
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    return jcs.canonicalize(payload)


def sign_resolution(private_key: Ed25519PrivateKey, payload: dict[str, Any]) -> str:
    signature = private_key.sign(canonical_bytes(payload))
    return base64.b64encode(signature).decode("ascii")


def verify_resolution(public_key: Ed25519PublicKey, payload: dict[str, Any], signature_b64: str) -> bool:
    try:
        sig = base64.b64decode(signature_b64.encode("ascii"))
        public_key.verify(sig, canonical_bytes(payload))
        return True
    except Exception:
        return False


def export_public_key_b64(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def load_public_key_b64(key_b64: str) -> Ed25519PublicKey:
    raw = base64.b64decode(key_b64.encode("ascii"))
    return Ed25519PublicKey.from_public_bytes(raw)
