# Deploying DR DOOM to Render

Two ways to deploy:

- **Option A — Blueprint (fastest):** push this repo to GitHub, then in Render
  click **New → Blueprint**, point it at the repo, and Render reads
  [`render.yaml`](render.yaml) to create the database, backend, and frontend
  in one go. Skip to [step 11](#11-verify-the-health-endpoint) once it's
  deployed, then fill in `CORS_ORIGINS` / `VITE_API_URL` with the real
  generated URLs if they differ from the guessed defaults in the blueprint.
- **Option B — Manual (full control):** follow steps 1–14 below.

> **Read this first:** Render's **Free** Postgres plan is time/size limited
> and Free web services spin down when idle (cold starts of ~30-60s are
> normal). This setup is a genuine, fully-functional demo/prototype
> deployment — not a promise of permanent medical-record storage or
> production-grade uptime. See README.md → "Render Free storage constraint".

---

## 1. Create a GitHub repository

```bash
git init
git add .
git commit -m "Initial commit: DR DOOM"
git branch -M main
git remote add origin https://github.com/<you>/dr-doom.git
```

## 2. Push the project

```bash
git push -u origin main
```

Make sure `backend/knowledge_base/index/`, `chunks/`, and `metadata/` are
committed (they're small — a few MB — and are the prebuilt knowledge base
the app serves from; see `.gitignore`, which deliberately excludes only the
large/regenerable `raw/`, `processed/`, `embeddings/` folders). If you
haven't built the index yet:

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -r requirements.txt
python scripts/ingest_documents.py
```

## 3. Create the Render PostgreSQL database

Render dashboard → **New → PostgreSQL**.
- Name: `drdoom-db`
- Plan: **Free**
- Region: pick the same region you'll use for the backend service.

Copy the **Internal Database URL** once it's provisioned — you'll need it
in step 5.

## 4. Create the backend Web Service

Render dashboard → **New → Web Service** → connect your repo.
- **Root Directory:** `backend`
- **Runtime:** Docker (it will detect `backend/Dockerfile`)
- **Plan:** Free
- **Health Check Path:** `/api/health`

## 5. Add backend environment variables

In the new service's **Environment** tab, add (see `.env.example` for the
full annotated list):

| Key | Value |
|---|---|
| `DATABASE_URL` | the Internal Database URL from step 3 |
| `SECRET_KEY` | a long random string (Render can auto-generate one) |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `none` (frontend/backend are different subdomains — see README "Privacy") |
| `MODEL_PROVIDER` | `template` (recommended for Free tier — see README "Model architecture") |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `VECTOR_INDEX_PATH` | `knowledge_base/index` |
| `KNOWLEDGE_VERSION` | `2026.08.1` |
| `CORS_ORIGINS` | the frontend URL you'll get in step 8 (fill in after, then redeploy) |
| `ENVIRONMENT` | `production` |

## 6. Deploy the backend

Click **Create Web Service**. First deploy takes a few minutes (installing
`faiss-cpu`, `onnxruntime`, etc.). Watch the logs for:

```
DR DOOM starting up (environment=production, model_provider=template)
Loaded knowledge base index: 476 chunks
DR DOOM startup complete.
```

## 7. Create the frontend Static Site

Render dashboard → **New → Static Site** → same repo.
- **Root Directory:** `frontend`
- **Build Command:** `npm install && npm run build`
- **Publish Directory:** `dist`
- **Rewrite rule:** add `/* → /index.html` (SPA routing) under **Redirects/Rewrites**.

## 8. Add `VITE_API_URL`

In the Static Site's **Environment** tab:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://<your-backend-service>.onrender.com` |

## 9. Deploy the frontend

Click **Create Static Site**.

## 10. Close the loop: set `CORS_ORIGINS` on the backend

Go back to the backend service's environment variables and set
`CORS_ORIGINS` to your frontend's real URL
(`https://<your-frontend-site>.onrender.com`), then **Manual Deploy →
Deploy latest commit** (or just save — Render redeploys on env var change).

## 11. Verify the health endpoint

```bash
curl https://<your-backend-service>.onrender.com/api/health
# {"status":"ok"}
curl https://<your-backend-service>.onrender.com/api/readiness
# {"ready":true,"checks":{"database":true,"knowledge_index":true,"model":true,...}}
```

If `knowledge_index` is `false`, the index wasn't committed to the repo (or
`VECTOR_INDEX_PATH` is wrong) — see step 2.

## 12. Test authentication

Open the frontend URL, register an account, and confirm you land on the
dashboard. If login appears to succeed but immediately bounces back to
`/login`, double-check `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true` on the
backend (cross-subdomain cookies need both) and that `CORS_ORIGINS` exactly
matches the frontend's origin (scheme + host, no trailing slash).

## 13. Test the RAG pipeline

Start a consultation and describe a symptom (e.g. "I've had a headache
since this morning"). Confirm: follow-up questions appear with clickable
options, a final assessment cites real MedlinePlus sources, and a chest-pain
scenario ("severe chest pain radiating to my arm with cold sweat") shows the
red emergency banner immediately.

## 14. Test voice and persistence

- Voice: tap the mic icon in a supported browser (Chrome/Edge) and confirm
  speech is transcribed into the composer; tap "Listen" on an assistant
  message to hear it read back.
- Persistence: refresh the page, open **History**, confirm the consultation
  is there; export its PDF summary; delete it and confirm it's gone.

---

## Troubleshooting

- **Backend takes a long time on first request after idling:** Render Free
  web services spin down after inactivity; the first request wakes it back
  up (cold start), which can take 30-60s. This is a Render Free
  characteristic, not an app bug.
- **`/api/readiness` shows `knowledge_index: false`:** the prebuilt index
  wasn't included in the deploy. Re-run `scripts/ingest_documents.py`
  locally, commit the output under `backend/knowledge_base/{index,chunks,metadata}`,
  and redeploy.
- **Login works locally but not on Render:** almost always a cookie
  `SameSite`/`Secure` or `CORS_ORIGINS` mismatch — see step 12.
- **Model provider shows `template_fallback` in `/api/admin/overview`:**
  expected if `MODEL_PROVIDER` is set to `local_transformers` or `ollama`
  but that backend isn't actually available in this environment — the app
  is falling back safely rather than failing (§47). Free tier RAM cannot
  reliably host `local_transformers` — leave `MODEL_PROVIDER=template`.
