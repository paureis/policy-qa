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

## Case routes (built Oct 26)

| Route | In | Out |
|---|---|---|
| `POST /case/intake` | multipart/form-data with exactly one of `file` (JPEG, PNG, WebP, or PDF, up to 10 MB, type read from the first bytes) or `text` (200 to 6,000 characters) | 200 `{case_id, source, raw_text, summary, card, model, cost_usd, latency_ms, status: "intake", created_at}` |
| `GET /case/{case_id}` | | the case, or 404 |
| `PATCH /case/{case_id}` | JSON object of plain values for any subset of the ten fields (dates `YYYY-MM-DD`, a range `YYYY-MM-DD/YYYY-MM-DD`, amount a number, selects the enum strings; `null` clears a non-enum field) | the full case; each edited cell becomes `{value, confidence: "high", edited: true}` |
| `POST /case/{case_id}/investigate` | | `{case_id, status: "investigating"}` (stub until the investigation agent lands) |

Errors come back as `{"detail": {"code", "message"}}`. Intake codes (422): `unsupported_type`, `too_large`, `text_length`, `unreadable`, `not_a_denial_letter`, `out_of_scope`; 400 `bad_request` for both or neither of file and text. Case codes: 404 `not_found`, 409 `wrong_status` (the card is editable only during intake), 422 `invalid_field` (with `field`). The screen shows the six intake codes with their own copy, any other 4xx message under "The service could not accept that", and a network failure or 5xx as "We could not reach the service".

After extraction, copied values (service code, amount, the three dates, payer) are checked against the letter text; a value that does not appear is demoted to `low` so the screen flags it, and the cell carries `verified: true|false`. Muse Spark 1.3 is a reasoning model, so completion tokens include its thinking (`reasoning_tokens` in the usage details) and every call carries a generous `max_tokens`.

Extraction runs on Muse Spark 1.3 (`policyqa/intake.py`, `MuseSparkExtractor`: text, `image_url`, or a PDF `file` part with a `pdftotext` fallback, JSON schema output) when `POLICYQA_LLM_BASE_URL` and `POLICYQA_LLM_MODEL` are set, and on `FixtureExtractor` (the Sunshine Health sample below, no network) otherwise. `GET /health` reports which in `intake`. Cases live in memory (`api/cases.py`) and vanish on restart.

### Intake screen modes

`NEXT_PUBLIC_INTAKE_MODE=fixture` (the default; `.env.example`) serves the sample case with no network and shows a "Sample case" tag; pasted text containing "dose", "dosage", "should I take", "diagnos", or "is it safe" shows the scope refusal, "[not a letter]" the not-a-denial-letter error, "[slow]" (or a file named with "slow") the 30-second timeout, a file named with "blank" the unreadable error. `NEXT_PUBLIC_INTAKE_MODE=live` calls the API at `NEXT_PUBLIC_API_URL`. The screen is built from `web/intake-brief.md`; pieces live in `src/components/intake/` and the client, types, and fixture in `src/lib/case.ts`.

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
    "payer_name":     {"value": "Sunshine Health", "confidence": "high"},
    "program":        {"value": "florida_medicaid_mma", "confidence": "high"},
    "member_age_group": {"value": "under_21", "confidence": "medium"},
    "service":        {"value": "private duty nursing, 8 hours/day", "confidence": "high"},
    "service_code":   {"value": "T1000", "confidence": "low"},
    "dates_of_service": {"value": "2026-09-01/2026-09-30", "confidence": "high"},
    "amount_billed":  {"value": 4320.00, "confidence": "medium"},
    "denial_reason":  {"value": "Services exceed the authorized amount.", "confidence": "high"},
    "letter_date":    {"value": "2026-10-14", "confidence": "high"},
    "appeal_deadline_claimed": {"value": "2026-12-13", "confidence": "medium"}
  }
}
```

The ten fields appear on the screen in this order. Program values: `florida_medicaid_mma`, `florida_medicaid_ltc`, `florida_kidcare`, `medicare_a`, `medicare_b`, `medicare_advantage`, `medicare_part_d`, `unknown`. Age groups: `under_21`, `adult`, `65_plus`, `unknown`. Confidence: `high`, `medium`, `low`; the screen flags medium and low for review.

`PATCH /case/{case_id}` takes any subset of card fields as plain values and returns the updated case. `POST /case/{case_id}/investigate` starts the investigation (contract follows when it lands). The intake screen has three states: uploading, reviewing the card, confirmed.
