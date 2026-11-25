# Learning Guide & 12-Hour Runbook

Rule: **do each step by typing it yourself, then read the "Why" line.** The viva will test understanding, not just working output.

## Hour-by-hour plan
| Time | Goal | Done when |
|---|---|---|
| 0:00–0:45 | Install tools, create repo, push scaffold | `docker`, `kubectl`, `kind`, `git` all run |
| 0:45–1:30 | Run app + tests + Docker locally | `curl localhost:8000/version` works |
| 1:30–3:00 | CI on `develop` + PR | green CI run link saved |
| 3:00–4:30 | kind cluster + manual `kubectl apply` once | 2 pods Running (you must understand it before automating) |
| 4:30–6:30 | Self-hosted runner + CD → **v1.0.0** | CD run green, `/version` = v1.0.0 |
| 6:30–8:00 | **v1.1.0** feature via PR + failing test demo | rolling update captured |
| 8:00–9:00 | **v1.2.0** bug fix | deployed |
| 9:00–11:00 | Report (PDF 5–10 p), slides (8–12), evidence | files ready |
| 11:00–12:00 | Buffer + rehearse live change | |

## Step 0 – Tools
Install Git, Docker Desktop (or Docker Engine), kubectl, kind, Python 3.12. Verify: `docker version`, `kubectl version --client`, `kind version`.

## Step 1 – Repo & branches
Follow **Part 4 of `RUN_AND_PUBLISH_GUIDE.md`** for the exact commands (note: `main` is pushed first WITHOUT the workflow files; they arrive via `develop` + a pull request so v1.0.0 is a PR-driven release).
*Why:* `main` = what is released; `develop` = integration. Protect `main` (Settings → Branches → require PR + passing CI). That is your "authorized release branch".

## Step 2 – Local run (understand before automating)
Follow README. Note: `APP_VERSION` is a Docker **build arg → ENV**, so `/version` proves which image runs.

## Step 3 – CI
Read `ci.yml` top to bottom. Key ideas: `needs:` creates the failure gate; `workflow_call` makes CI reusable by CD; Trivy `exit-code: 1` fails the build on serious vulnerabilities.
Open a PR `develop → main` and watch the Checks tab. **Save the URL.**
If Trivy fails on the base image, read the report: bump the base image tag (e.g. `python:3.12-slim` rebuild) or document an accepted risk.

## Step 4 – Kubernetes by hand first
```bash
kind create cluster --name campus --config kind-config.yaml
kubectl apply -f k8s/namespace.yaml -f k8s/configmap.yaml
kubectl -n campus-pulse create secret generic campus-pulse-secret --from-literal=API_KEY=dev-key
kind load docker-image campus-pulse:local --name campus
sed "s|IMAGE_PLACEHOLDER|campus-pulse:local|" k8s/deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/service.yaml
kubectl -n campus-pulse get pods -w
curl localhost:8080/version
```
Break it on purpose: `kubectl -n campus-pulse delete pod <name>` (watch self-healing); set a wrong image and watch `ImagePullBackOff`; `kubectl describe pod`, `kubectl logs`. This is your troubleshooting section.

## Step 5 – CD with a self-hosted runner
1. GitHub repo → Settings → Actions → Runners → New self-hosted runner → copy the commands it shows and run them on your laptop (Linux/macOS/WSL2 recommended; the workflow uses `bash`).
2. Settings → Secrets → Actions: add `APP_API_KEY` (any random string).
3. Settings → Environments → create `production` (optionally add yourself as required reviewer — great "approval" evidence).
4. Bump nothing; `VERSION` is `1.0.0`. Merge `develop → main` through a PR.
5. After `publish` succeeds: GitHub profile → Packages → your image → Package settings → **Change visibility → Public**, then re-run failed jobs. (Otherwise the cluster gets `ImagePullBackOff`.)
6. `curl localhost:8080/version` → `v1.0.0`.

*Why a self-hosted runner:* GitHub's cloud runners cannot reach `localhost` clusters. The runner polls GitHub outbound, so no inbound ports or kubeconfig leave your machine.

## Step 6 – Release v1.1.0 (feature) + the intentional CI failure
```bash
git switch develop && git switch -c feature/stats
```
Add to `create_app` in `app/main.py` (before `return app`):
```python
    @app.get("/stats")
    def stats():
        total = len(tasks)
        done = sum(1 for t in tasks.values() if t["done"])
        return jsonify(total=total, done=done, completion_rate=round(done / total * 100, 1))
```
Add test:
```python
def test_stats_with_tasks(client):
    tid = client.post("/tasks", json={"title": "a"}).get_json()["id"]
    client.put(f"/tasks/{tid}/done")
    assert client.get("/stats").get_json() == {"total": 1, "done": 1, "completion_rate": 100.0}
```
**Failing-test demo first:** commit with a wrong expectation (e.g. `"done": 2`), push, open PR → CI goes red. Screenshot it, explain the failure, fix, push → green. Nothing was published because CD only runs on `main`.
Then set `VERSION` to `1.1.0`, merge feature → develop → main. Watch: `kubectl -n campus-pulse rollout status deploy/campus-pulse` and `kubectl -n campus-pulse get pods -w` during the rolling update.

## Step 7 – Release v1.2.0 (bug fix)
The bug you just shipped: `GET /stats` with **zero tasks** divides by zero → HTTP 500. Document it as a GitHub Issue. Fix:
```python
        rate = round(done / total * 100, 1) if total else 0.0
```
Add the regression test:
```python
def test_stats_with_no_tasks(client):
    assert client.get("/stats").get_json()["completion_rate"] == 0.0
```
Set `VERSION` to `1.2.0`, PR → merge → deploy. Commit message: `fix: avoid division by zero in /stats (closes #1)`.

## Step 8 – Evidence checklist (per release)
`git log --oneline --graph` · Actions run URL · GHCR tag page · `kubectl rollout status` + `rollout history` output · `curl /version` · one red run + the green fix · screenshot of Secrets page (names only) · Trivy output.

## Step 9 – Rehearse the live change
Change the GREETING in `k8s/configmap.yaml` or add a tiny endpoint, bump `VERSION` to `1.2.1`, push through the branches, narrate each pipeline stage as it runs.

## Viva answers (short)
1. **CI** = automatically integrate + test every change. **Continuous Delivery** = every passing change is releasable, deploy needs a manual approval. **Continuous Deployment** = passing change auto-deploys with no human step. (Yours is deployment with an optional environment approval.)
2. Failed test → job fails → `needs` blocks publish and deploy; the previous version keeps running.
3. Tags are immutable identifiers: you can trace, roll back, and reproduce exactly what ran. `latest` moves and hides which code is live.
4. A container is one isolated process (image instance). A Pod is Kubernetes' smallest unit: wraps one or more containers sharing network/storage, with labels and lifecycle managed by controllers.
5. Deployment creates a new ReplicaSet and gradually scales it up while scaling the old one down, honouring `maxSurge`/`maxUnavailable`; readiness probes gate traffic. Yours: surge 1, unavailable 0.
6. Readiness = "send me traffic?" (failure removes the pod from the Service). Liveness = "am I stuck?" (failure restarts the container).
7. Self-hosted runner inside the network, or a least-privilege ServiceAccount token/kubeconfig stored in GitHub Secrets (ideally OIDC); never in git.
8. New pods never become Ready, so the rollout stalls while old pods keep serving; `rollout status` times out, and our workflow runs `rollout undo`.
9. `kubectl rollout undo deployment/campus-pulse` (or `--to-revision=N`), or redeploy the old image tag via the pipeline.
10. Reviewable, auditable, reproducible, revertible; the repo is the source of truth (basis of GitOps).

## Optional stretch (only after everything above works)
Helm chart · Argo CD · SBOM (`docker buildx ... --sbom=true`) · Prometheus/Grafana.
