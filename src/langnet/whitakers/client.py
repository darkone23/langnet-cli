from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

from langnet.clients.subprocess import SubprocessToolClient

logger = logging.getLogger(__name__)


class WhitakerClient:
    """
    Minimal Whitaker's Words client that returns lemma candidates.

    Parses lines with bracketed matches, e.g., "[is]" or "[idem]" and falls back to
    leading lemma tokens. No storage side effects; intended for normalization.
    """

    def __init__(self, binary: str | None = None) -> None:
        self.binary = binary or self._find_binary()

    def available(self) -> bool:
        return self.binary is not None

    def _find_binary(self) -> str | None:
        home_path = Path.home() / ".local" / "bin" / "whitakers-words"
        candidates = [
            home_path,
            Path(shutil.which("whitakers-words") or ""),
            Path(shutil.which("words") or ""),
        ]
        for path in candidates:
            if path and path.exists():
                return str(path)
        logger.debug("whitakers_binary_not_found")
        return None

    def fetch(self, query: str) -> list[str]:
        if not self.binary:
            return []

        client = SubprocessToolClient(tool="whitakers", command=[self.binary, query])
        effect = client.execute(call_id=f"whitakers-{query}")
        text = effect.body.decode("utf-8", errors="ignore")
        return self._parse_lemmas(text)

    def _parse_lemmas(self, text: str) -> list[str]:
        lemmas: list[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue

            if "[" not in line:
                continue

            # Take the first contiguous alphabetic run from the start of the line.
            m_head = re.match(r"^([A-Za-z]+)", line)
            if m_head:
                lemmas.append(m_head.group(1).lower())

        seen = set()
        out: list[str] = []
        for lemma in lemmas:
            if lemma not in seen:
                seen.add(lemma)
                out.append(lemma)
        return out
