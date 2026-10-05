from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class AssetKind(str, Enum):
    DONOR_RECEIPT = "donor_receipt"
    VOLUNTEER_REMINDER = "volunteer_reminder"
    CAMPAIGN_REPORT = "campaign_report"


class PublishRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    kind: AssetKind
    organization_name: str = Field(min_length=1, max_length=80)
    source_image: dict[str, str] = Field(min_length=1)


class PublishResult(BaseModel):
    asset_id: str
    kind: AssetKind
    state: str
    watermarked_image: dict[str, Any]


@dataclass(frozen=True)
class WatermarkRule:
    label: str
    position: str
    opacity: float


class WatermarkClient(Protocol):
    def add_watermark(
        self,
        *,
        image: dict[str, str],
        text: str,
        position: str,
        opacity: float,
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Return the processed image data for this publishing record."""


def rule_for(kind: AssetKind, organization_name: str) -> WatermarkRule:
    labels = {
        AssetKind.DONOR_RECEIPT: f"{organization_name} | DONOR COPY",
        AssetKind.VOLUNTEER_REMINDER: f"{organization_name} | VOLUNTEER UPDATE",
        AssetKind.CAMPAIGN_REPORT: f"{organization_name} | CAMPAIGN REPORT",
    }
    opacity = 0.55 if kind is AssetKind.DONOR_RECEIPT else 0.72
    return WatermarkRule(labels[kind], "bottom-right", opacity)


def publish_asset(request: PublishRequest, client: WatermarkClient) -> PublishResult:
    rule = rule_for(request.kind, request.organization_name)
    processed = client.add_watermark(
        image=request.source_image,
        text=rule.label,
        position=rule.position,
        opacity=rule.opacity,
        idempotency_key=f"nonprofit-watermark:{request.asset_id}",
    )
    return PublishResult(
        asset_id=request.asset_id,
        kind=request.kind,
        state="ready_to_publish",
        watermarked_image=processed,
    )
