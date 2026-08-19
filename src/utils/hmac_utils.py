import hashlib
import hmac


def generate_signature(
    payload: bytes,
    secret_key: str,
) -> str:
    """
    Создаёт HMAC-SHA256 подпись payload.

    Возвращает hex-строку.
    """
    return hmac.new(
        secret_key.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(
    payload: bytes,
    signature: str,
    secret_key: str,
) -> bool:
    """
    Проверяет HMAC-SHA256 подпись.
    """
    expected = generate_signature(
        payload=payload,
        secret_key=secret_key,
    )

    return hmac.compare_digest(
        expected,
        signature,
    )
