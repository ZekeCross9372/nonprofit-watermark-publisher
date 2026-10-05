from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .infrai_images import InfraiError, InfraiImageClient
from .publishing_policy import PublishRequest, PublishResult, publish_asset

app = FastAPI(title="Nonprofit image watermark publisher")


@app.post("/publish", response_model=PublishResult)
def publish(request: PublishRequest) -> PublishResult:
    client = InfraiImageClient()
    try:
        return publish_asset(request, client)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "error": exc.detail},
        ) from exc
    finally:
        client.close()

