# Arbiter

AI-first banking customer-service agent — built for the [Factored AI & Data Hackathon 2026](https://www.factored.ai/careers/ai-data-hackathon).

## Challenge

Build a focused AI-first workflow for banking customer service (e.g. account inquiries, card support, disputes, or credit eligibility) that goes beyond a chatbot: understanding, decision-making, action, verification, and escalation.

## Requirements

- Multilingual support (Spanish and Portuguese)
- Production-readiness over feature breadth
- Documented trade-offs: autonomy, accuracy, latency, cost, human oversight

## Deliverables

- [ ] Deployed solution (shareable link)
- [ ] 4–6 slide presentation
- [ ] Video pitch (max 3 min)

## Status

🚧 In progress — Challenge period: Sep 25 – Oct 5, 2026

## HTTP service

A minimal FastAPI scaffold under `app/` establishes a runnable application boundary before the decision pipeline (notebooks 01–09) is integrated. `GET /health` reports **HTTP application liveness only** — it does not check model readiness.

### Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

### Run locally

```bash
uvicorn app.main:app --reload
```

- Health: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI document: http://127.0.0.1:8000/openapi.json

Swagger UI loads its assets from a public CDN by default — a browser with internet access is required to view `/docs`.

### Smoke checks

```bash
curl -i http://127.0.0.1:8000/health
# HTTP/1.1 200 OK ... {"status":"ok"}

curl -f http://127.0.0.1:8000/docs

curl -fsS http://127.0.0.1:8000/openapi.json \
  | python -c 'import json,sys; assert "get" in json.load(sys.stdin)["paths"]["/health"]'
```

Editing and saving a file under `app/` triggers an automatic reload while `--reload` is running.

### Run in Docker

```bash
docker build -t factored-nba .
docker run -p 8000:8000 factored-nba
```

No Compose file, host ML dependencies, mounted artifacts, or application credentials are required. The container runs as a non-root user with a single Uvicorn process and no reload.

Repeat the same smoke checks above against `http://127.0.0.1:8000`.
