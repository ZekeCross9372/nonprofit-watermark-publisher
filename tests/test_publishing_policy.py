from typing import Any

import httpx

from nonprofit_watermark.infrai_images import InfraiImageClient

from nonprofit_watermark.publishing_policy import (
    AssetKind,
    PublishRequest,
    publish_asset,
)


class RecordingClient:
    def __init__(self) -> None:
        self.call: dict[str, Any] = {}

    def add_watermark(self, **values: Any) -> dict[str, Any]:
        self.call = values
        return {"id": "img_watermarked_42"}


def test_receipt_uses_quieter_mark_and_becomes_publishable() -> None:
    client = RecordingClient()
    request = PublishRequest(
        asset_id="receipt-2026-0042",
        kind=AssetKind.DONOR_RECEIPT,
        organization_name="River Pantry",
        source_image={"base64": "sample-image"},
    )

    result = publish_asset(request, client)

    assert client.call == {
        "image": {"base64": "sample-image"},
        "text": "River Pantry | DONOR COPY",
        "position": "bottom-right",
        "opacity": 0.55,
        "idempotency_key": "nonprofit-watermark:receipt-2026-0042",
    }
    assert result.state == "ready_to_publish"
    assert result.watermarked_image == {"id": "img_watermarked_42"}


def test_campaign_report_uses_standard_visibility() -> None:
    client = RecordingClient()
    request = PublishRequest(
        asset_id="report-spring-2026",
        kind=AssetKind.CAMPAIGN_REPORT,
        organization_name="River Pantry",
        source_image={"base64": "sample-image"},
    )

    publish_asset(request, client)

    assert client.call["text"] == "River Pantry | CAMPAIGN REPORT"
    assert client.call["opacity"] == 0.72


def test_image_process_uses_ops_instead_of_top_level_watermark_fields() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/image/process"
        import json

        assert json.loads(request.content) == {
            "image": {"base64": "sample-image"},
            "ops": [{
                "op": "watermark",
                "params": {
                    "text": "River Pantry | DONOR COPY",
                    "position": "bottom-right",
                    "opacity": 0.55,
                },
            }],
        }
        return httpx.Response(200, json={"ok": True, "data": {"id": "processed"}})

    client = InfraiImageClient(api_key="test", transport=httpx.MockTransport(respond))
    try:
        result = client.add_watermark(
            image={"base64": "sample-image"},
            text="River Pantry | DONOR COPY",
            position="bottom-right",
            opacity=0.55,
            idempotency_key="receipt-test",
        )
        assert result == {"id": "processed"}
    finally:
        client.close()
