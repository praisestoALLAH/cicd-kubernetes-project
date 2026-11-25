# Run, Test and Publish Guide (step by step)

Read once top to bottom, then follow the parts in order. Every command is meant to be typed by you; after each part there is a **Check** so you know it worked before moving on.

- Part 1 - Install the tools
- Part 2 - Run and test the app on your computer
- Part 3 - Run it in Docker
- Part 4 - Publish the project to GitHub
- Part 5 - Turn on CI and protect `main`
- Part 6 - Create the Kubernetes cluster and deploy by hand once
- Part 7 - Set up automated deployment (secrets, runner, environment)
- Part 8 - Release v1.0.0, v1.1.0, v1.2.0 (including the failing test)
- Part 9 - Collect evidence and submit
- Part 10 - Troubleshooting

---
## Part 1 - Install the tools

You need: **Git, Python 3.12, Docker, kubectl, kind** (and a GitHub account).

### Windows (recommended path: WSL2)
1. Open PowerShell **as Administrator**: `wsl --install -d Ubuntu` and restart when asked. Open the "Ubuntu" app and create a username/password.
2. Install **Docker Desktop**, then Settings -> Resources -> WSL integration -> enable **Ubuntu**.
3. Do ALL remaining commands inside the Ubuntu terminal (not PowerShell). Install the rest there:
```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip curl
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/ && rm kubectl
# kind
curl -Lo kind https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-amd64
sudo install kind /usr/local/bin/ && rm kind
```

### macOS
```bash
brew install git python@3.12 kubectl kind
brew install --cask docker     # then open Docker Desktop once
```

### Linux (Ubuntu/Debian)
Use the same `apt` / `kubectl` / `kind` commands as the WSL block above, and install Docker Engine from https://docs.docker.com/engine/install/ (then `sudo usermod -aG docker $USER` and log out/in).

### Check
```bash
git --version; python3 --version; docker version --format '{{.Server.Version}}'; kubectl version --client; kind version
```
All five must print a version. If `docker version` shows a connection error, start Docker Desktop.

Also tell Git who you are (one time):
```bash
git config --global user.name  "Your Name"
git config --global user.email "your-github-email@example.com"
git config --global init.defaultBranch main
```

---
## Part 2 - Run and test the app locally

1. Unzip `campus-pulse.zip`. Rename the folder to `cicd-kubernetes-project` (this is the repo name used in the docs) and open a terminal in it.
2. Create an isolated Python environment (so packages do not pollute your system):
```bash
python3 -m venv .venv
source .venv/bin/activate          # prompt now starts with (.venv)
pip install -r requirements.txt -r requirements-dev.txt
```
3. **Lint** (code style/quality) and **test**:
```bash
flake8 app tests        # no output = clean
pytest -v               # expect: 6 passed
```
4. Start the app:
```bash
python -m flask --app app.main run --port 8000
```
5. In a **second** terminal, exercise every endpoint:
```bash
curl localhost:8000/health
curl localhost:8000/version                       # {"commit":"unknown","version":"dev"}
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Revise Docker","course":"Infra"}'
curl localhost:8000/tasks
curl -X PUT localhost:8000/tasks/1/done
curl localhost:8000/tasks/1
curl -X DELETE localhost:8000/tasks/1 -i          # 204
```
6. Try the API key feature: stop the app (Ctrl+C), then
```bash
API_KEY=letmein python -m flask --app app.main run --port 8000
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"x"}'                          # 401
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" -H "X-API-Key: letmein" -d '{"title":"x"}' # 201
```
### Check
Tests pass, `/health` returns `{"status":"ok"}`, and the 401 -> 201 behaviour works. Save a screenshot of `pytest -v` (evidence #2). Stop the app with Ctrl+C.

**Learn:** the tests use Flask's test client, so they run without a server - this is why CI can run them in seconds.

---
## Part 3 - Run it in Docker

```bash
docker build --build-arg APP_VERSION=v-local --build-arg GIT_SHA=local123 -t campus-pulse:local .
docker run -d --name cp -p 8000:8000 campus-pulse:local
sleep 5
curl localhost:8000/version        # shows v-local / local123 (baked in at build time)
docker ps                          # STATUS should become "healthy" after ~30s
docker logs cp
docker rm -f cp
```
### Check
`docker ps` shows `(healthy)`. Screenshot it (evidence #3).

**Learn:** change a line in `app/main.py` and rebuild - the dependency layer is cached (look for `CACHED`), so the rebuild is fast.

---
## Part 4 - Publish the project to GitHub

### 4.1 Create the account and empty repository
1. Sign up/in at https://github.com.
2. Click **+** -> **New repository**. Name: `cicd-kubernetes-project`. Visibility: **Public** (simplest: the instructor can see it, and branch protection/environments work on the free plan). **Do NOT** tick "Add a README/.gitignore/licence" - the project already has them.
3. Click **Create repository**. Copy the URL: `https://github.com/YOUR-USERNAME/cicd-kubernetes-project.git`.

### 4.2 Authenticate (pick ONE)
**Option A - GitHub CLI (easiest):**
```bash
# install: brew install gh   |   sudo apt install gh   (or https://cli.github.com)
gh auth login          # GitHub.com -> HTTPS -> Login with a web browser
gh auth setup-git
```
**Option B - Personal Access Token:** GitHub -> Settings -> Developer settings -> Personal access tokens -> Tokens (classic) -> Generate. Tick scopes **repo**, **workflow** and **write:packages**. When `git push` asks for a password, paste the token (not your account password).

### 4.3 Push the code
Run inside the project folder. **Important:** we push `main` WITHOUT the workflow files first. If the CD workflow existed on `main` right now, it would fire immediately - before your cluster, secret and runner exist. Instead, the workflows arrive later through `develop` and a pull request, which makes v1.0.0 a proper PR-driven release.
```bash
git init -b main
git add .
git rm -r --cached .github -q        # un-stage the workflows for now (files stay on disk)
git status                           # confirm .venv/, secret files and .github are NOT in the commit list
git commit -m "chore: initial project scaffold"
git remote add origin https://github.com/YOUR-USERNAME/cicd-kubernetes-project.git
git push -u origin main
```
Now create the integration branch and add the workflows there:
```bash
git switch -c develop
git add .github
git commit -m "ci: add CI and CD workflows"
git push -u origin develop           # this push triggers the CI workflow
```
### Check
Refresh GitHub: branches `main` and `develop` exist; `.github/workflows/` is only on `develop`. Open the **Actions** tab: a **CI** run for your `develop` push is running (that is your first pipeline run).

> **Security check before every push:** `git status` must never show `k8s/secret.yaml`, `.env` or a kubeconfig. If you ever commit a real secret, treat it as leaked: rotate it, don't just delete the file.

---
## Part 5 - Turn on CI and protect `main`

1. CI already started when you pushed `develop` in Part 4. To trigger it again at any time, make a change on `develop` and push (e.g. `echo "" >> README.md && git commit -am "docs: touch" && git push`).
2. GitHub -> **Actions** -> open the **CI** run. Watch jobs `Lint + unit tests` then `Docker build + smoke test + vulnerability scan`. Click into each step and read the logs (this is what you will explain in the viva).
3. If the Trivy step fails on a base-image vulnerability, read the table it prints. Fix by rebuilding on a newer base (edit the `FROM` tag, e.g. `python:3.12.7-slim`) or updating the vulnerable dependency in `requirements.txt`, then push again.
4. Open a pull request: **Pull requests -> New pull request -> base: `main`, compare: `develop`**. The checks run on the PR. Do **not** merge yet - merging this PR IS the v1.0.0 release (Part 8), and it must wait until the cluster, secret and runner are ready.
5. Protect `main`: **Settings -> Branches -> Add branch protection rule** -> pattern `main` -> tick **Require a pull request before merging** and **Require status checks to pass** (search and add `Lint + unit tests` and `Docker build + smoke test + vulnerability scan`; they appear after the first CI run) -> **Create**.

### Check
You have a green CI run (save URL, evidence #5/#6) and `main` shows a "protected" badge (evidence #15).

---
## Part 6 - Create the cluster and deploy by hand once

Doing it manually first means you understand what the pipeline will automate.

```bash
kind create cluster --name campus --config kind-config.yaml
kubectl cluster-info --context kind-campus
kubectl get nodes                                   # 2 nodes, STATUS Ready
```
Load your local image into the cluster (kind cannot see your local Docker images otherwise):
```bash
kind load docker-image campus-pulse:local --name campus
kubectl apply -f k8s/namespace.yaml -f k8s/configmap.yaml
kubectl -n campus-pulse create secret generic campus-pulse-secret --from-literal=API_KEY=dev-key
sed "s|IMAGE_PLACEHOLDER|campus-pulse:local|" k8s/deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/service.yaml
kubectl -n campus-pulse get pods -w                 # wait for 2/2 Running, Ctrl+C
curl localhost:8080/
curl localhost:8080/version
```
Experiments (each teaches a viva answer):
```bash
kubectl -n campus-pulse delete pod <one-pod-name>     # self-healing: a new pod appears
kubectl -n campus-pulse scale deployment campus-pulse --replicas=3
kubectl -n campus-pulse describe pod <pod-name>       # events, probes, resources
kubectl -n campus-pulse logs <pod-name>
kubectl -n campus-pulse set image deployment/campus-pulse app=campus-pulse:doesnotexist   # watch ImagePullBackOff
kubectl -n campus-pulse rollout undo deployment/campus-pulse                              # recover
kubectl -n campus-pulse scale deployment campus-pulse --replicas=2
```
### Check
`curl localhost:8080/` returns the greeting "Hello from Campus Pulse on Kubernetes" (proof the ConfigMap works). Save `kubectl -n campus-pulse get all` (evidence #8).

Clean up the manual deploy before automating, so the pipeline starts from a clean slate: `kubectl delete namespace campus-pulse`.

---
## Part 7 - Set up automated deployment

### 7.1 Add the secret
GitHub repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**. Name `APP_API_KEY`, value any long random string (e.g. output of `openssl rand -hex 16`).

### 7.2 Create the environment (optional approval step)
**Settings -> Environments -> New environment** -> name exactly `production`. Optionally add yourself under **Required reviewers**: every deployment then pauses for your click (excellent evidence of a controlled release; remember to approve during the demo!). If your repo is private on a free plan and environments are unavailable, either make the repo public or delete the line `environment: production` from `.github/workflows/cd.yml`.

### 7.3 Install the self-hosted runner (on the machine running kind)
1. GitHub repo -> **Settings -> Actions -> Runners -> New self-hosted runner** -> choose your OS (Linux for WSL2/Ubuntu, macOS for Mac).
2. Copy the commands GitHub shows (download, extract, `./config.sh --url ... --token ...`) and run them in a folder **outside** the project, e.g. `~/actions-runner`. Accept defaults. The token is shown only on that page and expires quickly - do not share or commit it.
3. Start it:
```bash
cd ~/actions-runner
./run.sh                    # leave this terminal open during demos
```
4. Verify the runner has what the deploy job needs:
```bash
which kubectl docker python3 curl
kubectl get nodes           # must work as the same user that runs the runner
```
### Check
Settings -> Runners shows your runner as **Idle** (green). Screenshot it (evidence #14).

> **Security:** a self-hosted runner executes workflow code on your machine. Only the `deploy` job uses it and it runs only on pushes to `main` (never on pull requests), so strangers cannot trigger it. Also set **Settings -> Actions -> General -> Fork pull request workflows -> Require approval for all outside collaborators**.

### 7.4 Make the image pullable
The first CD run publishes the image to GHCR as a **private** package, so the cluster cannot pull it. After the first `publish` job succeeds:
GitHub profile -> **Packages** -> `cicd-kubernetes-project` -> **Package settings** -> **Change visibility -> Public**. Then in the failed CD run click **Re-run failed jobs**.

---
## Part 8 - The three releases

The `VERSION` file decides the tag. **Bump it in every release PR**, otherwise the publish job correctly refuses to overwrite an existing tag.

### Release v1.0.0 (initial)
VERSION already contains `1.0.0`.
1. Open PR `develop` -> `main` (Part 5), wait for green checks, **Merge pull request**.
2. Actions -> **CD** run starts: `Validate` -> `Publish` -> `Deploy`. If you set required reviewers, click **Review deployments -> Approve**.
3. Do the one-time package visibility step (7.4) if the deploy shows `ImagePullBackOff`.
4. Verify:
```bash
kubectl -n campus-pulse get pods
kubectl -n campus-pulse rollout history deployment/campus-pulse
curl localhost:8080/version          # {"commit":"<sha>","version":"v1.0.0"}
```
Capture evidence #7, #9, #12, #16.

### Release v1.1.0 (feature + intentional failure)
```bash
git switch develop && git pull
git switch -c feature/stats
```
1. Edit `app/main.py`: before `return app` add:
```python
    @app.get("/stats")
    def stats():
        """Totals and completion percentage for all tasks."""
        total = len(tasks)
        done = sum(1 for t in tasks.values() if t["done"])
        return jsonify(total=total, done=done, completion_rate=round(done / total * 100, 1))
```
2. Edit `tests/test_app.py` - add a test with a **deliberately wrong** expectation:
```python
def test_stats_with_tasks(client):
    """Stats reflect created and completed tasks."""
    task_id = client.post("/tasks", json={"title": "a"}).get_json()["id"]
    client.put(f"/tasks/{task_id}/done")
    assert client.get("/stats").get_json() == {"total": 1, "done": 2, "completion_rate": 100.0}
```
3. Run `pytest` locally - it fails (`done` is 1, not 2). Commit and push anyway, then open a PR `feature/stats` -> `develop`:
```bash
git add -A && git commit -m "feat: add /stats endpoint (with wrong test on purpose)"
git push -u origin feature/stats
```
4. Watch CI go **red** at the test step; the Docker job is skipped. Screenshot the failed run and the log line showing the assertion (evidence #4). Explain: *a test failed, so nothing was built or published.*
5. Fix the test (`"done": 1`), commit, push -> CI turns green:
```bash
git commit -am "fix(test): correct expected done count"
git push
```
6. Bump the version and finish:
```bash
echo "1.1.0" > VERSION
git commit -am "chore: release 1.1.0"
git push
```
7. Merge the PR into `develop`, then open PR `develop` -> `main`, merge it. CD runs and performs the **rolling update**. Watch it live in another terminal:
```bash
kubectl -n campus-pulse get pods -w
kubectl -n campus-pulse rollout history deployment/campus-pulse
curl localhost:8080/version          # v1.1.0
curl localhost:8080/stats
```
Capture evidence #10, #11, #12.

### Release v1.2.0 (bug fix)
1. Reproduce the bug on the live app (no tasks exist after the pods restarted): `curl -i localhost:8080/stats` -> **HTTP 500** (division by zero). Open a GitHub **Issue** titled "GET /stats returns 500 when there are no tasks" and paste the output.
2. ```bash
   git switch develop && git pull && git switch -c fix/stats-zero-division
   ```
3. Fix `app/main.py`:
```python
        # Avoid dividing by zero when there are no tasks yet
        rate = round(done / total * 100, 1) if total else 0.0
        return jsonify(total=total, done=done, completion_rate=rate)
```
4. Add the regression test to `tests/test_app.py`:
```python
def test_stats_with_no_tasks(client):
    """Regression test: /stats must not crash when there are no tasks."""
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert resp.get_json()["completion_rate"] == 0.0
```
5. ```bash
   pytest -v                       # 8 passed
   echo "1.2.0" > VERSION
   git add -A && git commit -m "fix: avoid division by zero in /stats (closes #1)"
   git push -u origin fix/stats-zero-division
   ```
6. PR -> `develop` -> PR -> `main`. After CD: `curl -i localhost:8080/stats` -> **200** and `/version` -> `v1.2.0`.

### Optional: demonstrate automatic rollback
Create a throwaway branch, break `/health` (return status 500) with a matching passing test change, bump VERSION to `1.2.1`, merge. The rollout stalls, `rollout status` times out, the pipeline runs `rollout undo` and the app stays on v1.2.0. Revert that change afterwards (and never reuse the burned version number).

---
## Part 9 - Evidence, report and submission

1. Take the screenshots in `docs/evidence/README.md` and save them in `docs/evidence/`.
2. The report (`docs/submission/Technical_Report.pdf`) contains **orange [bracketed] placeholders and dashed "[INSERT EVIDENCE]" boxes**. Fill in your name, student number, repo URL, run URLs and paste your screenshots. Easiest route: come back to me with your real details, run URLs and screenshots, and I will regenerate the PDF with everything filled in.
3. Fill in the same placeholders on slides 1 and 10 of `Presentation.pptx` (name, number).
4. Commit the evidence and docs:
```bash
git switch develop && git pull
git add docs && git commit -m "docs: add evidence, report and slides"
git push
```
   then PR to `main`. Docs-only merges do not trigger CD (the workflow ignores `docs/**` and `*.md`), so no new version is needed.
5. Make sure the instructor can open the repo (public, or invite them under Settings -> Collaborators).
6. Submit: repo URL, `Technical_Report.pdf`, `Presentation.pptx`, evidence links.

### Final checklist
- [ ] 3+ endpoints, `/health`, `/version`, tests, README
- [ ] Dockerfile + .dockerignore; image on GHCR with v1.0.0, v1.1.0, v1.2.0
- [ ] CI on develop pushes + PRs; red run and green run saved
- [ ] 2 replicas, Service, ConfigMap, Secret, both probes, resources, RollingUpdate
- [ ] CD deploys on merge to main, waits for rollout, verifies, reports
- [ ] No real secrets in git (`git log -p | grep -i api_key` shows nothing real)
- [ ] You can explain every file and answer the 10 questions in `docs/LEARNING_GUIDE.md`
- [ ] Rehearsed the live change (Part 8 steps, small edit + version bump)

---
## Part 10 - Troubleshooting

| Problem | Fix |
|---|---|
| `permission denied` on `docker` (Linux) | `sudo usermod -aG docker $USER`, log out and in |
| `pytest: ModuleNotFoundError: app` | Run from the project root (where `pytest.ini` is) with the venv active |
| `git push` rejected / asks password forever | Use `gh auth login`, or a token with `repo`+`workflow` scopes |
| CI not starting | Workflows must be under `.github/workflows/`; CI triggers on `develop` pushes and PRs; check the Actions tab is enabled |
| Trivy fails the build | Read the table; update base image/dependency; rerun |
| `publish` fails "tag already exists" | Bump `VERSION` (immutability check working) |
| Deploy job waits forever | Runner offline - run `./run.sh`; check labels `self-hosted` |
| `kubectl: command not found` in deploy | Runner service has a different PATH - start it from your terminal with `./run.sh` |
| `ImagePullBackOff` | Set the GHCR package to public (7.4), re-run failed jobs |
| `localhost:8080` refused | Cluster was not created with `kind-config.yaml`: `kind delete cluster --name campus` and recreate |
| Rollout timeout | `kubectl -n campus-pulse describe pod <pod>` and `logs`; probe path/port or crash |
| After laptop reboot, nothing works | Start Docker, then `docker start campus-control-plane campus-worker` (or recreate cluster) and `./run.sh` |
