# Recourse web

Next.js 16 (App Router, TypeScript, Tailwind 4) front end. Scaffolded with `create-next-app` on Oct 26, 2026; everything else is built during the hackathon.

```bash
cd web
npm install
cp .env.example .env.local     # NEXT_PUBLIC_API_URL, default http://localhost:8000
npm run dev                    # http://localhost:3000
```

Run the API next to it from the repo root:

```bash
pip install -e ".[api]"
uvicorn api.main:app --reload --port 8000
```

## API contract (day one)

| Route | In | Out |
|---|---|---|
| `GET /health` | | `{ok, index_built, dense_built, model}` |
| `GET /search?q=&k=` | question, k (1 to 10) | `{query, hits: [{chunk_id, doc_id, page, title, jurisdiction, score, text}]}` |
| `POST /answer` | `{question, k}` | `{question, answer, abstained, citations: [{passage, doc_id, page, quote, overlap}], passages, citations_proposed, citations_dropped, forced_abstain, model, input_tokens, output_tokens, cost_usd, latency_ms, error, trace}` |

The case routes (intake from image, PDF, or text; investigate; verdict; letter) are added as the agent is built and documented here as they land.

## Design

The UI is built with the Impeccable skill installed globally on the developer machine: `/impeccable init` writes `PRODUCT.md`, `shape` plans a view, `craft` builds it, `critique`, `audit`, and `polish` review it. Those files are committed when they exist.

## Case card contract (intake)

`POST /case/intake` takes one of `file` (image or PDF, multipart) or `text`, and returns a case:

```json
{
  "case_id": "c_1a2b3c",
  "source": "image | pdf | text",
  "raw_text": "the letter as read",
  "card": {
    "program":        {"value": "florida_medicaid_mma", "confidence": "high"},
    "member_age_group": {"value": "under_21", "confidence": "medium"},
    "service":        {"value": "private duty nursing, 8 hours/day", "confidence": "high"},
    "service_code":   {"value": "T1000", "confidence": "low"},
    "dates_of_service": {"value": "2026-09-01/2026-09-30", "confidence": "high"},
    "amount_billed":  {"value": 4320.00, "confidence": "medium"},
    "denial_reason":  {"value": "Services exceed the authorized amount.", "confidence": "high"},
    "letter_date":    {"value": "2026-10-14", "confidence": "high"},
    "appeal_deadline_claimed": {"value": "2026-12-13", "confidence": "medium"},
    "payer_name":     {"value": "Sunshine Health", "confidence": "high"}
  }
}
```

Program values: `florida_medicaid_mma`, `florida_medicaid_ltc`, `florida_kidcare`, `medicare_a`, `medicare_b`, `medicare_advantage`, `medicare_part_d`, `unknown`. Age groups: `under_21`, `adult`, `65_plus`, `unknown`. Confidence: `high`, `medium`, `low`; the screen flags medium and low for review.

`PATCH /case/{case_id}` takes any subset of card fields as plain values and returns the updated case. `POST /case/{case_id}/investigate` starts the investigation (contract follows when it lands). The intake screen has three states: uploading, reviewing the card, confirmed.
