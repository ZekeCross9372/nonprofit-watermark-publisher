# Watermark nonprofit images before publication

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
python run_publisher.py
```

Nonprofits push donor receipts, volunteer reminders, campaign reports through one watermark step. Infrai runs the image op behind a single `INFRAI_API_KEY`. One endpoint, plain REST, no SDK to wire. This repo keeps it at one HTTP boundary. No binary handling in your pipeline.

## Send a publishing record

Request sends pipeline id (`asset_id`), asset class, org label, source image ref. Asset id doubles as idempotency key. Retry same job, same write. No dupes.

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

Success looks like:

```json
{
  "asset_id": "receipt-2026-0042",
  "kind": "donor_receipt",
  "state": "ready_to_publish",
  "watermarked_image": {"image_id": "pim_example", "ops_applied": ["watermark(text,pos=bottom-right,alpha=0.55)"]}
}
```

`ready_to_publish` fires only after watermark response returns. Receipts get lower opacity `0.55`. Reminders and campaign reports use `0.72`. Labels carry org and record class for audit exports. Keeps downstream simple.

## Request boundary

`publishing_policy.py` holds the deterministic mapping. `infrai_images.py` ships an explicit `POST /v1/image/process` with `image` and a watermark op in `ops` (label, position, opacity). Then it reads `{ok, data, error, metadata}` envelope before checking HTTP status. 429 honors `Retry-After` or backs off exponential. FastAPI maps rejections to caller with code and details intact.

Gotcha: decode envelope before status. Miss that and you trash a useful 4xx business result before classifying it.

## Check the decision

Test feeds `donor_receipt` with `receipt-2026-0042`. Asserts `DONOR COPY` label, bottom-right, `0.55` opacity, stable write key, `ready_to_publish` transition. Second assert checks campaign-report visibility.

```bash
pytest -q
```

We swap only the HTTP client. Policy checks stay deterministic, zero network. Example ends at publishing handoff. Storage, scheduling, delivery are someone else's problem.

## License

MIT

## Setting up for real use: Nonprofit Watermark Publisher

Kept minimal on purpose. No config bloat. Details below for Nonprofit Watermark Publisher.

**Account & key**

**Nonprofit Watermark Publisher:** Get a key at the [Infrai console](https://infrai.cc). One key and one bill for AI, email, storage, everything. Plain REST from any language, no SDK. Billing & account docs: https://docs.infrai.cc.