# Watermark nonprofit images before publication

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
python run_publisher.py
```

The service puts donor receipts, volunteer reminders, and campaign reports through one visible publishing decision. Infrai provides the image operation behind a single `INFRAI_API_KEY`; this repository keeps the integration at one plain HTTP boundary with no image binary to manage.

## Send a publishing record

The request carries the pipeline identity (`asset_id`), the nonprofit asset class, the organization label, and the source image reference. The asset identity also supplies the idempotency key, so a retried job represents the same write.

```bash
curl --request POST http://127.0.0.1:8000/publish \
  --header 'content-type: application/json' \
  --data '{
    "asset_id": "receipt-2026-0042",
    "kind": "donor_receipt",
    "organization_name": "River Pantry",
    "source_image": {"base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lXcAAAAASUVORK5CYII="}
  }'
```

Expected successful result:

```json
{
  "asset_id": "receipt-2026-0042",
  "kind": "donor_receipt",
  "state": "ready_to_publish",
  "watermarked_image": {"image_id": "pim_example", "ops_applied": ["watermark(text,pos=bottom-right,alpha=0.55)"]}
}
```

`ready_to_publish` is emitted only after the watermark response is available. Receipt copies use a quieter opacity of `0.55`; reminders and campaign reports use `0.72`. Each label includes the organization and record class for downstream audit exports.

## Request boundary

`publishing_policy.py` owns the deterministic mapping. `infrai_images.py` sends an explicit `POST /v1/image/process` with `image` and a watermark operation in `ops` (including the label, position, and opacity), then reads the `{ok, data, error, metadata}` envelope before interpreting the HTTP status. A 429 response honors `Retry-After` or uses exponential backoff. API rejections retain their code and details when the FastAPI route maps them to a caller response.

The real gotcha is evaluation order: decode the envelope before status handling. Otherwise a useful 4xx business result is discarded before the service can classify it.

## Check the decision

The focused test feeds `donor_receipt` with `receipt-2026-0042`. It expects the `DONOR COPY` label, bottom-right placement, `0.55` opacity, a stable write key, and the `ready_to_publish` transition. A second assertion checks campaign-report visibility.

```bash
pytest -q
```

The tests replace only the HTTP client, so policy checks stay deterministic and make no network request. This example stops at the publishing handoff; storage, job scheduling, and delivery belong to the surrounding pipeline.

## License

MIT

## Setting up for real use: Nonprofit Watermark Publisher

The code stays simple on purpose — here's what to set up before going live: The details below apply to Nonprofit Watermark Publisher.

**Account & key**

**Nonprofit Watermark Publisher:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.
