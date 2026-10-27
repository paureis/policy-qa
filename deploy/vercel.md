# Front end on Vercel

The front end is the Next.js 16 app in `web/`. It reads two variables, both in `web/src/lib/case.ts`:

| Variable | Value for the live demo | What it does |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<workspace>--recourse-api.modal.run` (no trailing slash needed; it is stripped) | Base URL of the API |
| `NEXT_PUBLIC_INTAKE_MODE` | `live` | `live` calls the API; anything else serves the fixture sample case with no network |

`NEXT_PUBLIC_*` values are compiled into the bundle at build time. Changing one in Vercel does nothing until you redeploy.

## Before you start

Build once on your machine, so a Vercel build failure is not the first time you see it:

```powershell
cd ~\recourse\web
npm ci
npm run build
```

Expected: `next build` ends with the route table and no error. If it fails here, it fails on Vercel too.

## Create the project (dashboard, recommended)

The dashboard avoids the Vercel CLI picking the wrong team on a machine with several accounts.

1. vercel.com, **Add New...** then **Project**.
2. **Import** the GitHub repo `paureis/recourse`. Check the team shown at the top of the import screen is the one you want.
3. **Root Directory**: click **Edit**, choose `web`. Framework Preset should read **Next.js** by itself.
4. Leave Build Command (`next build`) and Install Command (npm, from `package-lock.json`) at their defaults.
5. **Environment Variables**: add `NEXT_PUBLIC_API_URL` = the Modal URL from the runbook step that printed it, and `NEXT_PUBLIC_INTAKE_MODE` = `live`.
6. **Deploy**. Wait for "Congratulations" and note the production domain, for example `https://recourse-xyz.vercel.app`.

If you use the CLI instead: run `vercel whoami` and `vercel teams ls` first and check the active team, then `vercel link` from `web/`.

## Tell the API about the front end (CORS)

The browser calls the API from the Vercel domain, so the API must list that domain in `RECOURSE_CORS_ORIGINS` (read by `api/main.py`, comma separated, exact origins, no trailing slash). The Modal app takes it from the shell that runs `modal deploy`:

```powershell
cd ~\recourse
$env:RECOURSE_CORS_ORIGINS = "https://recourse-xyz.vercel.app,http://localhost:3000"
modal deploy deploy/modal_app.py
```

Use the production domain. Preview deployments get a different domain per branch and commit and will fail CORS: the API takes exact origins only (no wildcard), so test previews in fixture mode or add their domain to the list. Page images (`<img>` tags) load without CORS; intake, case polling, and highlight lookups need it.

Redeploying the API restarts its container. A case in progress at that moment stops and stays in `investigating`. Do it before the demo, not during one.

## Check it

1. Open the production domain. The intake screen should not show the "Sample case" tag (that tag means fixture mode).
2. Browser dev tools, Network tab, paste a sample denial letter and submit. The `POST .../case/intake` request goes to the Modal URL and returns 200. A CORS error in the Console means the origin list does not match the domain exactly.

## Fixture fallback

If the API is down, out of model credits, or misbehaving during judging:

1. Vercel project, **Settings**, **Environment Variables**: set `NEXT_PUBLIC_INTAKE_MODE` to `fixture`.
2. **Deployments**, the latest production deployment, **...**, **Redeploy**.

The site then serves the Sunshine Health sample case with no network calls and shows the "Sample case" tag, so nobody mistakes it for a live run. Set it back to `live` and redeploy to return.

The API has its own fallback too: without the `recourse-muse-spark` secret values, or without the index on the volume, `/health` reports `"investigation": "fixture"` and the chain runs on fixtures.

## Not verified

Nothing was deployed when this was written. Unverified: that Next 16.4.3 with `cacheComponents` and the Turbopack Tailwind loader builds on Vercel's default Node version, and the exact dashboard labels (written from Vercel's current flow; check them as you go).
