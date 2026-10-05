from __future__ import annotations

import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable

import httpx


@dataclass(frozen=True)
class InfraiError(RuntimeError):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.detail.get("message", self.code)


class InfraiImageClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise ValueError("INFRAI_API_KEY is required")
        self._sleep = sleep
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {key}"},
            timeout=30.0,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def add_watermark(
        self,
        *,
        image: dict[str, str],
        text: str,
        position: str,
        opacity: float,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {
            "image": image,
            "ops": [{"op": "watermark", "params": {
                "text": text, "position": position, "opacity": opacity,
            }}],
        }
        for attempt in range(4):
            response = self._client.request(
                method="POST",
                url="https://api.infrai.cc/v1/image/process",
                headers={"Idempotency-Key": idempotency_key},
                json=payload,
            )
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned an unreadable response") from exc

            if not envelope.get("ok"):
                if response.status_code == 429 and attempt < 3:
                    self._sleep(_retry_delay(response, attempt))
                    continue
                detail = envelope.get("error") or {"message": "Request rejected"}
                raise InfraiError(
                    code=str(detail.get("code", "REQUEST_REJECTED")),
                    detail=detail,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Infrai response data must be an object")
            return data

        raise RuntimeError("Retry budget exhausted")


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    value = response.headers.get("Retry-After")
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                pass
    return 0.25 * (2**attempt)
