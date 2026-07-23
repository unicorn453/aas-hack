"""BaSyx path identifiers are UTF8-BASE64-URL-encoded (see /v3/api-docs)."""

import base64


def encode_id(identifier: str) -> str:
    return base64.urlsafe_b64encode(identifier.encode("utf-8")).decode("ascii")


def decode_id(encoded: str) -> str:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
