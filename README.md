# Campus Pulse – End-to-End CI/CD with GitHub, Docker & Kubernetes

A small study-task tracker API (Flask) used to demonstrate a fully automated pipeline:
**GitHub → CI (lint, test, build, scan) → GHCR (versioned image) → CD → Kubernetes rolling update.**

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | App info (greeting comes from ConfigMap) |
| GET | `/health` | Health check (used by probes + Docker HEALTHCHECK) |
| GET | `/version` | Running release (baked into image at build time) |
| GET/POST | `/tasks` | List (optional `?course=`) / create tasks |
| GET/DELETE | `/tasks/<id>` | Fetch / delete a task |
| PUT | `/tasks/<id>/done` | Mark task done |

Write requests need header `X-API-Key` when `API_KEY` is set (from a Kubernetes Secret).

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
flake8 app tests && pytest -v
python -m flask --app app.main run --port 8000
```

## Run with Docker
```bash
docker build --build-arg APP_VERSION=v1.0.0 -t campus-pulse:local .
docker run -p 8000:8000 campus-pulse:local
curl localhost:8000/version
```

## Pipeline
| Workflow | Trigger | Stages |
|---|---|---|
| `ci.yml` | push to `develop`, PR to `main`/`develop` | lint → pytest → docker build → container smoke test → Trivy scan |
| `cd.yml` | push (merge) to `main` | reuse CI → publish `ghcr.io/<owner>/<repo>:vX.Y.Z` → deploy → rollout wait → verify `/version` → auto-rollback on failure |

A failing test stops the workflow before any image is published or deployed.

**Tagging:** the `VERSION` file is the single source of truth. Image tags are immutable
(`v1.0.0`, `v1.1.0`, …) plus `sha-<commit>`. CD refuses to overwrite an existing tag. `latest` is not used.

## Kubernetes (`k8s/`)
Deployment (2 replicas, RollingUpdate, probes, requests/limits) · Service (NodePort) ·
ConfigMap (non-sensitive) · Secret (created by CD from GitHub secret `APP_API_KEY`; `secret.example.yaml` is a template only).

## Reproduce the deployment
1. `kind create cluster --name campus --config kind-config.yaml`
2. Install a self-hosted runner on a machine that can run `kubectl` against the cluster (GitHub → Settings → Actions → Runners).
3. Add secret `APP_API_KEY` and an Environment named `production`.
4. Merge to `main`. After the first publish, set the GHCR package to **public** (or add an imagePullSecret) and re-run the deploy job.
5. Open http://localhost:8080/version

## Security notes
Non-root container user · slim base image · Trivy gate (CRITICAL/HIGH) · no secrets in git (`.gitignore`) ·
GHCR login via short-lived `GITHUB_TOKEN` · least-privilege workflow `permissions` · Secret injected at deploy time.

## Evidence and guides
See `docs/RUN_AND_PUBLISH_GUIDE.md` (full step-by-step), `docs/LEARNING_GUIDE.md`, `docs/evidence/` and `docs/architecture.md`.
