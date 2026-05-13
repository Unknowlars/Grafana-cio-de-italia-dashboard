# Giro d'Italia 2026 Race Control Dashboard

This repo runs a local Grafana stack with a live Giro d'Italia race-control dashboard.

The dashboard is designed to answer the questions a viewer usually has during a stage:

- What is happening in the race right now?
- Who is at the front?
- How far is left?
- How fast is the race going?
- What are the latest official race updates?
- Who leads the GC and jersey classifications?
- How is INEOS / Netcompany Ineos doing?

The main dashboard is:

```text
Giro d'Italia 2026 - Race Control v12
```

## How It Works

The stack has three main services:

- `lgtm`: Grafana, provisioned with the dashboard JSON and Infinity datasource.
- `giro-data`: a small FastAPI service that fetches and normalizes official Giro data.
- `renderer`: Grafana image renderer.

Grafana reads panel-ready JSON from `giro-data` through the Infinity datasource. The service keeps Grafana queries simple and avoids fragile dashboard-side parsing for standings, HTML headlines, team filtering, race state, and numeric KPIs.

Primary official sources:

- Livefeed JSON: `https://www.giroditalia.it/en/livefeed/tappa/${stage}/`
- Headlines JSON: `https://www.giroditalia.it/en/headlines/`
- Classifications page: `https://www.giroditalia.it/en/classifiche/`

The dashboard does not fabricate live race data. If a source cannot be parsed, the relevant panel should show source status or no data rather than made-up standings.

## Prerequisites

- Docker
- Docker Compose
- Internet access from Docker containers
- Ports available by default:
  - Grafana: `3009`
  - Giro data service: `8088`
  - Prometheus: `9092`
  - Tempo: `3200`
  - Loki: `3400`
  - Pyroscope: `3500`

## Quick Start

Clone the repo:

```bash
git clone <repo-url>
cd grafana-stack
```

Create or edit `.env`:

```bash
cp .env.example .env
```

If there is no `.env.example`, create `.env` with at least:

```bash
TZ=Europe/Copenhagen
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
RENDERER_TOKEN=change-me-to-any-long-random-string
GRAFANA_PORT=3009
GIRO_DATA_PORT=8088
```

Start the stack:

```bash
docker compose up -d --build
```

Open Grafana:

```text
http://localhost:3009
```

Default login:

```text
admin / admin
```

Open the dashboard:

```text
http://localhost:3009/d/giro-race-control-v12/giro-d-italia-2026-race-control-v12
```

Useful stage-5 URL:

```text
http://localhost:3009/d/giro-race-control-v12/giro-d-italia-2026-race-control-v12?orgId=1&from=now-6h&to=now&timezone=browser&var-DS_INFINITY=infinity&var-stage=5&var-watched_team_code=NCI&refresh=30s
```

## Service Checks

Check the local data service:

```bash
curl http://localhost:8088/health
curl http://localhost:8088/api/v1/stage/5/race-now
curl "http://localhost:8088/api/v1/standings/gc?limit=5"
curl "http://localhost:8088/api/v1/standings/team?limit=5"
```

Check running containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f giro-data
docker compose logs -f lgtm
```

## Dashboard Source

The dashboard source of truth is the Python builder:

```text
scripts/build_giro_race_control_v12.py
```

It generates:

```text
grafana/dashboards/giro-ditalia-2026-race-control-v12.json
```

Regenerate and validate the dashboard:

```bash
python3 scripts/build_giro_race_control_v12.py
```

The builder validates:

- no duplicate panel IDs
- no grid overflow
- no visible overlap
- every panel has a description
- every Infinity query has a datasource ref
- risky UQL patterns are avoided

## Main Dashboard Sections

- `Race right now`: stage status, progress, km to go, km done, speed, elapsed time, feed refresh, and latest official situation.
- `Front of race`: race groups, front riders, INEOS watch badge, and latest official updates.
- `INEOS watch`: INEOS riders visible live, INEOS in the front group, official update mentions, and INEOS GC context.
- `GC & jerseys`: official GC, points, mountains, youth, and Super Team top five.
- `Details / Debug / Sources`: collapsed by default; source health, weather, raw normalized feeds, and source notes.

## Common Troubleshooting

If Grafana shows no dashboard:

```bash
docker compose down -v
docker compose up -d --build
```

If panels show no data, check:

```bash
curl http://localhost:8088/health
docker compose logs --tail=100 giro-data
```

If Infinity blocks the local service, confirm `grafana/provisioning/datasources/datasource.yml` includes:

```yaml
allowedHosts:
  - http://giro-data:8080
```

If the dashboard URL changes after a manual import, use the provisioned UID:

```text
/d/giro-race-control-v12/giro-d-italia-2026-race-control-v12
```

## Stop The Stack

Stop containers but keep volumes:

```bash
docker compose down
```

Reset Grafana data and re-provision from files:

```bash
docker compose down -v
docker compose up -d --build
```
