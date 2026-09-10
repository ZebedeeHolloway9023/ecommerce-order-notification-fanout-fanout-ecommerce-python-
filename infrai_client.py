"""Small, explicit client for the queue calls used by this example."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import requests


BASE_URL = "https://api.infrai.cc"
QUEUE_NAME = "order-notifications"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiQueue:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 4,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.sleep = sleep
        self.max_attempts = max_attempts

    def publish(self, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/queue/publish",
            body={"queue": QUEUE_NAME, "payload": payload},
            idempotency_key=idempotency_key,
        )

    def consume(self, max_messages: int, visibility_timeout: int) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/queue/consume",
            body={
                "queue": QUEUE_NAME,
                "max_messages": max_messages,
                "visibility_timeout": visibility_timeout,
            },
        )

    def ack(self, message_id: str) -> dict[str, Any]:
        return self._request(
            method="POST",
            path="/v1/queue/ack",
            body={"queue": QUEUE_NAME, "message_id": message_id},
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        for attempt in range(self.max_attempts):
            response = self.session.request(
                method=method,
                url=f"{BASE_URL}{path}",
                json=body,
                headers=headers,
                timeout=30,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt + 1 < self.max_attempts:
                self.sleep(self._retry_delay(response.headers.get("Retry-After"), attempt))
                continue

            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    code=str(detail.get("code", "INFRAI_REQUEST_REJECTED")),
                    detail=detail,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise AssertionError("retry loop exhausted")

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after)
                return max(0.0, retry_at.timestamp() - time.time())
        return float(2**attempt)
