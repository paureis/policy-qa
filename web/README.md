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
