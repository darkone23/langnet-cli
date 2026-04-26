from __future__ import annotations

import hashlib


def local_raw_response_id(tool: str, endpoint: str, body: bytes) -> str:
    """Build a deterministic raw response id for local, content-addressed fetches."""
    material = b"\0".join([tool.encode("utf-8"), endpoint.encode("utf-8"), body])
    digest = hashlib.sha256(material).hexdigest()[:16]
    return f"raw-{tool.replace('.', '-')}-{digest}"
