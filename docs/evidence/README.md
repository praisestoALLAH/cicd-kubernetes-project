# Evidence checklist

Save screenshots in this folder using these names, then paste them into the report (placeholders are in orange).
Never include secret VALUES in screenshots - secret NAMES are fine.

| # | File name | What to capture | Command / page |
|---|-----------|-----------------|----------------|
| 1 | 01-branches-and-prs.png | Branch list + merged PRs | GitHub -> Pull requests (Closed) |
| 2 | 02-local-tests.png | 6 tests passing locally | `pytest -v` |
| 3 | 03-docker-local.png | Container running + /version | `docker ps`, `curl localhost:8000/version` |
| 4 | 04-ci-red.png | FAILED CI run (intentional) | Actions -> failed run, open the test job log |
| 5 | 05-ci-green.png | Fixed, successful CI run | Actions -> green run |
| 6 | 06-trivy.png | Vulnerability scan output | Actions -> docker job -> Trivy step |
| 7 | 07-ghcr-tags.png | v1.0.0, v1.1.0, v1.2.0 tags | GitHub profile -> Packages |
| 8 | 08-k8s-get-all.png | 2 pods Running, service | `kubectl -n campus-pulse get all` |
| 9 | 09-cd-v1.0.0.png | CD run + summary | Actions -> CD run |
| 10 | 10-rollout-v1.1.0.png | Rolling update in progress | `kubectl -n campus-pulse get pods -w` during deploy |
| 11 | 11-rollout-history.png | Revision history | `kubectl -n campus-pulse rollout history deployment/campus-pulse` |
| 12 | 12-version-each-release.png | /version for each release | `curl localhost:8080/version` |
| 13 | 13-secrets-page.png | Secret names only | Settings -> Secrets and variables -> Actions |
| 14 | 14-runner-online.png | Self-hosted runner "Idle" | Settings -> Actions -> Runners |
| 15 | 15-branch-protection.png | Protected main | Settings -> Branches |
| 16 | 16-git-log.png | Commit history per release | `git log --oneline --graph --decorate` |

## Links to record (paste into the report appendix)
- Failed run URL:
- Successful CI run URL:
- CD run v1.0.0 / v1.1.0 / v1.2.0 URLs:
- GHCR package URL:
