from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from raccoon_guardian.domain.models import NotificationResult


class SlackNotifier:
    def __init__(self, webhook_url: str | None, enabled: bool) -> None:
        self.webhook_url = webhook_url
        self.enabled = enabled

    def send_message(
        self,
        text: str,
        *,
        blocks: list[dict[str, Any]] | None = None,
    ) -> NotificationResult:
        if not self.enabled:
            return NotificationResult(
                delivered=False,
                channel="slack",
                detail="slack delivery is disabled in config",
            )
        if not self.webhook_url:
            return NotificationResult(
                delivered=False,
                channel="slack",
                detail="slack webhook URL is not configured",
            )

        payload: dict[str, Any] = {"text": text}
        if blocks is not None:
            payload["blocks"] = blocks
        req = request.Request(
            self.webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=5) as response:
                detail = f"slack webhook accepted with HTTP {response.status}"
        except error.URLError as exc:
            return NotificationResult(
                delivered=False,
                channel="slack",
                detail=f"slack delivery failed: {exc.reason}",
            )
        return NotificationResult(delivered=True, channel="slack", detail=detail)
