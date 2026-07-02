# Lambda Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the always-on ECS Fargate + ALB + NAT-Gateway backend for `nj-bioenergy-api.apps.qsdsan.com` with an AWS Lambda container-image function behind a Function URL, so cost tracks actual (near-zero) usage instead of 24/7 uptime.

**Architecture:** The existing FastAPI/uvicorn app runs inside a Lambda container image unmodified, using the AWS Lambda Web Adapter extension (proxies Lambda invocations to the app's own HTTP port — no rewrite into a native Lambda handler). A Lambda Function URL is the public HTTPS entry point (chosen over API Gateway because Function URLs allow up to Lambda's own 15-minute timeout, versus API Gateway's hard 29-second cap — a cold biosteam/thermosteam import plus a full system build-and-simulate can plausibly run long). The function needs no VPC attachment (no DB or private-network dependency exists in the app), which removes the NAT Gateway cost entirely, not just shrinks it. The existing CloudFront distribution keeps the same custom domain and ACM cert; only its origin is swapped from the ECS `.on.aws` endpoint to the new Function URL. The old ECS service/ALB are paused (not deleted) after cutover, pending a burn-in period.

**Tech Stack:** AWS Lambda (container image, x86_64), AWS Lambda Web Adapter (`public.ecr.aws/awsguru/aws-lambda-adapter`), Lambda Function URL, existing ECR repo `nj-bioenergy-api` (qsdsan-app account, us-east-2), existing CloudFront distribution `d3t3sqyyjalry1.cloudfront.net`, GitHub Actions (extends the existing OIDC-to-ECR pipeline).

## Global Constraints

- All work is committed directly to `main` in the `nj-bioenergy-api` repo (no feature branch) — but each commit still requires explicit user approval before it's made; changes are surfaced as a diff first.
- No changes to the app's business logic (`app/services/*_calc*`, `app/routers/*`) — only the filesystem fix needed for Lambda's read-only filesystem.
- No VPC attachment for the Lambda function (nothing in the app talks to a private network resource — verified: no `requests`/`boto3`/`sqlalchemy`/database calls anywhere in `app/`).
- The public custom domain `nj-bioenergy-api.apps.qsdsan.com` and its CloudFront distribution/ACM cert do not change — only the CloudFront **origin** changes.
- The existing ECS service, ALB, target groups, and VPC/NAT Gateway are **paused, not deleted**, until the Lambda path has run in production through a burn-in period. Rollback = point CloudFront origin back at the `.on.aws` endpoint.
- Tasks 1-3 are code/CI changes executed in this repo. Tasks 4-8 are AWS console/CLI steps — **the assistant has no AWS credentials in this environment and will not execute them**; they're written as an exact runbook for whoever has the `yalin-admin` → `qsdsan-app` switch-role access documented in `deployments/qsdsan.md`.
- No local Docker install required: the image is smoke-tested inside GitHub Actions (which has Docker on its hosted runners) rather than on a local machine, since neither the assistant's environment nor the user's local machine has Docker available.

---

## File Structure

- Modify: `app/services/htl_service.py` — delete the dead `EXPOSAN_RESULTS_PATH` block (defined, `os.makedirs`'d at import time, then never read anywhere in the repo). Under Lambda, that unconditional `os.makedirs` outside `/tmp` would throw `OSError: Read-only file system` during the cold-start import and crash the function before it could serve a single request — deleting it removes the crash without needing to preserve a value nothing consumes.
- Modify: `app/services/combustion_service.py` — same deletion; same dead-code shape.
- Create: `Dockerfile.lambda` — Lambda container-image variant of the existing `Dockerfile` (same builder stage; runtime stage adds the Lambda Web Adapter extension and points every scientific-library cache directory at `/tmp`, since numba/matplotlib/etc. can still try to write to a home-directory cache on import even after the dead-code deletion above).
- Create: `.github/workflows/build-and-push-lambda.yml` — manual-dispatch-only CI workflow that builds `Dockerfile.lambda`, smoke-tests it two ways (plain app boot check, then a Lambda Runtime Interface Emulator check of the adapter path) on GitHub's hosted runner in place of a local Docker install, pushes it to the existing ECR repo under a `lambda-*` tag only if both checks pass, and (once the function exists, added in Task 6) updates the Lambda function's code.

---

### Task 1: Delete the dead EXPOSAN_RESULTS_PATH code

**Files:**
- Modify: `app/services/htl_service.py`
- Modify: `app/services/combustion_service.py`

**Interfaces:** none (pure deletion, no new symbols produced or consumed).

- [ ] **Step 1: Update `app/services/htl_service.py`**

Replace:

```python
# for file paths
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define a relative path inside the project
EXPOSAN_RESULTS_PATH = os.path.join(BASE_DIR, "..", "exposan_results")

if not os.path.exists(EXPOSAN_RESULTS_PATH):
    os.makedirs(EXPOSAN_RESULTS_PATH, exist_ok=True)

from exposan.htl import create_model # exposan version @ git+https://github.com/QSD-Group/EXPOsan.git@93d4173347019ab0d4d5c325501ea35d3f947439
```

with:

```python
# for file paths
import os

from exposan.htl import create_model # exposan version @ git+https://github.com/QSD-Group/EXPOsan.git@93d4173347019ab0d4d5c325501ea35d3f947439
```

Note: this file separately redefines `BASE_DIR` a few lines later for `CSV_PATH` (`BASE_DIR = os.path.dirname(os.path.abspath(__file__))` followed by `CSV_PATH = os.path.join(BASE_DIR, "..", "data", "htl", "htl_data.csv")`) — that block is unrelated and stays untouched; `import os` stays too since that later block still needs it.

- [ ] **Step 2: Update `app/services/combustion_service.py`**

Replace:

```python
import biosteam as bst

# for file paths
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define a relative path inside the project
EXPOSAN_RESULTS_PATH = os.path.join(BASE_DIR, "..", "exposan_results")

if not os.path.exists(EXPOSAN_RESULTS_PATH):
    os.makedirs(EXPOSAN_RESULTS_PATH, exist_ok=True)

from exposan import htl
```

with:

```python
import biosteam as bst

# for file paths
import os

from exposan import htl
```

Same note as above: this file's own `BASE_DIR`/`CSV_PATH` block for `combustion_data.csv` is defined again further down and is untouched.

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `uv run pytest -v` (or, if `uv run` fails to resolve the venv, `./.venv/Scripts/python.exe -m pytest -v` on Windows)
Expected: all tests still pass — the deleted code had no callers, so nothing should change behaviorally.

- [ ] **Step 4: Commit**

```bash
git add app/services/htl_service.py app/services/combustion_service.py
git commit -m "Delete unused EXPOSAN_RESULTS_PATH code that crashes on Lambda's read-only filesystem"
```

---

### Task 2: Lambda container image (Dockerfile.lambda)

**Files:**
- Create: `Dockerfile.lambda`

**Interfaces:**
- Consumes: same `pyproject.toml`/`uv.lock` and `app/` tree as the existing `Dockerfile`; no new interfaces produced (this is a build artifact, not a Python module).

- [ ] **Step 1: Create `Dockerfile.lambda`**

```dockerfile
# Lambda container-image variant of the FastAPI backend.
#
# Reuses the same dependency-build stage as the ECS Dockerfile. The
# runtime stage differs in two ways:
#   1. It adds the AWS Lambda Web Adapter as an extension, which lets the
#      existing uvicorn/FastAPI app run inside Lambda completely
#      unmodified (the adapter proxies Lambda invocations to HTTP calls
#      against the app's own port).
#   2. It points every cache/config directory the scientific stack might
#      write to (numba JIT cache, matplotlib font cache, etc.) at /tmp,
#      since Lambda's filesystem is read-only everywhere else.

FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install -y gcc g++ gfortran git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

FROM python:3.10-slim AS runtime

RUN apt-get update && apt-get install -y libopenblas0 liblapack3 && rm -rf /var/lib/apt/lists/*

COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=5000
ENV AWS_LWA_READINESS_CHECK_PATH=/health

ENV HOME=/tmp
ENV XDG_CACHE_HOME=/tmp/.cache
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

COPY --from=builder /app/.venv /app/.venv

WORKDIR /app

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
```

- [ ] **Step 2: Commit**

```bash
git add Dockerfile.lambda
git commit -m "Add Lambda container-image variant of the backend Dockerfile"
```

---

### Task 3: CI workflow — build, smoke-test, and push the Lambda image

No local Docker install available (neither the assistant's environment nor the user's machine has it), so this task moves what would otherwise be a local smoke test into GitHub Actions, which already has Docker on its hosted runners. Nothing is pushed to ECR unless both smoke-test steps pass first.

**Files:**
- Create: `.github/workflows/build-and-push-lambda.yml`

**Interfaces:**
- Consumes: repo secret `AWS_GHA_ROLE_ARN` (already exists, reused from `build-and-push-ecr.yml`).
- Produces: an ECR image tagged `lambda-latest` and `lambda-<git-sha>` in the existing `nj-bioenergy-api` ECR repo, only once the image has been smoke-tested inside the same job.

- [ ] **Step 1: Create the workflow**

```yaml
name: Build, smoke-test, and push Lambda image to ECR

# Manual-dispatch only, on purpose: the Lambda function doesn't exist yet
# (Task 4 creates it by hand), and this shouldn't run automatically on
# every push to main until the Lambda path has been cut over to in
# production. Once that's done, this can be folded into the normal
# push-triggered pipeline like build-and-push-ecr.yml.
#
# Runs on GitHub's hosted runner (which already has Docker) instead of
# requiring a local Docker install, and smoke-tests the image two ways
# before ever pushing to ECR:
#   1. Plain app boot check - confirms uvicorn/FastAPI actually starts
#      and answers requests (catches import errors, etc).
#   2. Lambda Runtime Interface Emulator check - confirms the AWS Lambda
#      Web Adapter correctly proxies a Lambda-invocation-shaped request
#      to the app, which the plain check above doesn't exercise.

on:
  workflow_dispatch: {}

permissions:
  id-token: write
  contents: read

env:
  AWS_REGION: us-east-2
  ECR_REPOSITORY: nj-bioenergy-api
  IMAGE_TAG: nj-bioenergy-api:lambda-smoketest

jobs:
  build-smoketest-and-push:
    runs-on: ubuntu-latest
    steps:
      - name: Check out the repo
        uses: actions/checkout@v4

      - name: Build Lambda image
        run: docker build -f Dockerfile.lambda -t "$IMAGE_TAG" .

      - name: Smoke test 1 - plain app boot check
        run: |
          docker run -d --rm -p 5000:5000 --name lambda-smoketest-app "$IMAGE_TAG"

          echo "Waiting for /health to respond..."
          healthy=""
          for i in $(seq 1 60); do
            if curl -sf http://localhost:5000/health > /dev/null; then
              healthy="1"
              echo "Healthy after $((i * 10))s"
              break
            fi
            sleep 10
          done
          if [ -z "$healthy" ]; then
            echo "App never became healthy within 600s"
            docker logs lambda-smoketest-app
            exit 1
          fi

          echo "Checking a real HTL calculation..."
          http_code=$(curl -s -o /tmp/htl_response.json -w "%{http_code}" "http://localhost:5000/api/v1/htl/calc?kg_hr=150")
          cat /tmp/htl_response.json
          if [ "$http_code" != "200" ]; then
            echo "HTL calc endpoint returned $http_code"
            docker logs lambda-smoketest-app
            exit 1
          fi

          docker stop lambda-smoketest-app

      - name: Smoke test 2 - Lambda Runtime Interface Emulator check
        run: |
          mkdir -p /tmp/aws-lambda-rie
          curl -Lo /tmp/aws-lambda-rie/aws-lambda-rie \
            https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie
          chmod +x /tmp/aws-lambda-rie/aws-lambda-rie

          docker run -d --rm -p 9000:8080 \
            -v /tmp/aws-lambda-rie:/aws-lambda \
            --entrypoint /aws-lambda/aws-lambda-rie \
            --name lambda-smoketest-rie \
            "$IMAGE_TAG" /opt/extensions/lambda-adapter

          echo "Waiting for the RIE endpoint to come up..."
          up=""
          for i in $(seq 1 30); do
            if curl -sf -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
                 -d '{"version":"2.0","routeKey":"$default","rawPath":"/health","requestContext":{"http":{"method":"GET","path":"/health"}},"headers":{}}' \
                 > /tmp/rie_response.json; then
              up="1"
              break
            fi
            sleep 10
          done
          cat /tmp/rie_response.json || true
          if [ -z "$up" ] || ! grep -q '"statusCode":200' /tmp/rie_response.json; then
            echo "RIE invocation did not return statusCode 200"
            docker logs lambda-smoketest-rie
            exit 1
          fi

          docker stop lambda-smoketest-rie

      - name: Configure AWS credentials (OIDC, no stored keys)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_GHA_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Log in to Amazon ECR
        id: ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Tag and push Lambda image
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
        run: |
          IMAGE="$REGISTRY/$ECR_REPOSITORY"
          docker tag "$IMAGE_TAG" "$IMAGE:lambda-${{ github.sha }}"
          docker tag "$IMAGE_TAG" "$IMAGE:lambda-latest"
          docker push "$IMAGE:lambda-${{ github.sha }}"
          docker push "$IMAGE:lambda-latest"
          echo "Pushed $IMAGE:lambda-latest and :lambda-${{ github.sha }}"
```

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/build-and-push-lambda.yml
git commit -m "Add CI workflow to build, smoke-test, and push the Lambda image"
git push
```

- [ ] **Step 3: Run it once by hand and confirm the image lands in ECR**

In GitHub: Actions tab → "Build, smoke-test, and push Lambda image to ECR" → Run workflow → select the `main` branch.

Expected: green run through both smoke-test steps (check the "Checking a real HTL calculation..." log line for the actual cold-start duration — **note it**, since it directly informs the Lambda memory/timeout starting values in Task 4); then, in the AWS console (or CLI, after switch-role into `qsdsan-app`):

```bash
aws ecr describe-images --repository-name nj-bioenergy-api --region us-east-2 \
  --query "imageDetails[?contains(imageTags, 'lambda-latest')]"
```

Expected: one image entry with `lambda-latest` in `imageTags`.

---

### Task 4 (AWS runbook — human-executed): Create the Lambda function

**Files:** none (AWS console/CLI)

> Everything from here on touches the live `qsdsan-app` AWS account. Sign in as `yalin-admin` (management account) → Switch Role → `qsdsan-app` (476663692697) → role `OrganizationAccountAccessRole`, region **us-east-2** (per `deployments/qsdsan.md`). Nothing here modifies the existing ECS/ALB/CloudFront resources yet — this only creates new, additional resources.

- [ ] **Step 1: Create the IAM execution role**

Console: IAM → Roles → Create role → AWS service → Lambda → attach `AWSLambdaBasicExecutionRole` (CloudWatch Logs only — no VPC-access policy needed, since this function won't be in a VPC). Name it `nj-bioenergy-api-lambda-execution`.

- [ ] **Step 2: Create the function from the ECR image**

Console: Lambda → Create function → "Container image" → function name `nj-bioenergy-api` → browse to the `nj-bioenergy-api` ECR repo, tag `lambda-latest` → architecture `x86_64` → execution role: use existing → `nj-bioenergy-api-lambda-execution`.

- [ ] **Step 3: Set memory, timeout, and ephemeral storage**

Configuration → General configuration → Edit:
- Memory: start at **3008 MB** (Lambda allocates CPU proportional to memory; this targets roughly 1.7 vCPU-equivalent, since the CloudWatch data pulled from the current ECS task shows real requests saturate a full 1 vCPU almost to 100% — under-provisioning memory here would make cold requests even slower, not just cheaper).
- Timeout: start at **60 seconds**. Revisit based on the cold-start duration you observed in Task 3, Step 3's CI logs — if a cold `htl/calc` request took close to 60s there, raise this (Function URLs support up to 900s, unlike API Gateway).
- Ephemeral storage (`/tmp`): raise from the 512 MB default to **1024 MB** (numba JIT cache lands in `/tmp` now).

Expected: saved without error; note the actual cold-start duration from the first test invocation in Task 5 and come back to tune memory/timeout if needed — these are starting points, not final values.

- [ ] **Step 4: Smoke-test the function directly (bypassing everything else)**

Console: Lambda function → Test tab → create a test event using the "apigw-request" or a raw HTTP-proxy-shaped payload:

```json
{
  "version": "2.0",
  "routeKey": "$default",
  "rawPath": "/health",
  "requestContext": {
    "http": {
      "method": "GET",
      "path": "/health"
    }
  },
  "headers": {}
}
```

Expected: `"statusCode": 200` with a body matching the `/health` response. If it errors, check CloudWatch Logs for the function (Lambda auto-creates a log group `/aws/lambda/nj-bioenergy-api`) before proceeding.

---

### Task 5 (AWS runbook — human-executed): Function URL

**Files:** none (AWS console/CLI)

- [ ] **Step 1: Create the Function URL**

Console: the function → Configuration → Function URL → Create function URL.
- Auth type: **NONE** (matches the current ALB's behavior — it's a public API today; the app's own CORS allowlist and rate-limiting middleware are the actual access controls, same as in production now).
- CORS: configure to mirror `_DEFAULT_ALLOWED_ORIGINS` in `app/main.py:51-54` — allow origin `https://nj-bioenergy.apps.qsdsan.com`, methods `*`, headers `*`. This is defense-in-depth alongside the app's own `CORSMiddleware`; keep both.

- [ ] **Step 2: Test the Function URL directly, before touching CloudFront**

```bash
curl -s "https://<function-url-id>.lambda-url.us-east-2.on.aws/health"
curl -s "https://<function-url-id>.lambda-url.us-east-2.on.aws/api/v1/htl/calc?kg_hr=150"
```

Expected: same responses as the CI smoke tests in Task 3. Time the second call — this is your first real signal for whether the Task 4 Step 3 memory/timeout values need adjusting before this goes anywhere near the custom domain.

---

### Task 6 (AWS runbook — human-executed): Wire CI to auto-deploy

**Files:**
- Modify: `.github/workflows/build-and-push-lambda.yml` (adds a deploy step, now that the function exists)

- [ ] **Step 1: Grant the CI role permission to update the function**

Console: IAM → Roles → `github-actions-ecr-push` (the role `build-and-push-ecr.yml` already assumes via OIDC) → Add permissions → attach an inline policy scoped to `lambda:UpdateFunctionCode` on the `nj-bioenergy-api` function's ARN only (not `*`).

- [ ] **Step 2: Add the deploy step to the workflow**

Append to the `build-smoketest-and-push` job in `.github/workflows/build-and-push-lambda.yml`, after the "Tag and push Lambda image" step:

```yaml
      - name: Update Lambda function code
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
        run: |
          aws lambda update-function-code \
            --function-name nj-bioenergy-api \
            --image-uri "$REGISTRY/$ECR_REPOSITORY:lambda-${{ github.sha }}" \
            --region ${{ env.AWS_REGION }}
```

- [ ] **Step 3: Commit, run the workflow once by hand, confirm the function picks up the new image**

```bash
git add .github/workflows/build-and-push-lambda.yml
git commit -m "Auto-update the Lambda function on image push"
git push
```

Then Actions tab → run the workflow manually → confirm in the Lambda console that "Last modified" updates and the image digest matches the new push.

---

### Task 7 (AWS runbook — human-executed): CloudFront cutover

**Files:** none (AWS console/CLI)

- [ ] **Step 1: Record the current origin for rollback**

Console: CloudFront → distribution `d3t3sqyyjalry1.cloudfront.net` → Origins tab → note down the current origin domain (the `.on.aws` ECS Express endpoint) and its origin request/cache policy names (`CachingDisabled` / `AllViewerExceptHostHeader` per `deployments/qsdsan.md`) — this is exactly what you'll restore if you need to roll back.

- [ ] **Step 2: Swap the origin**

Origins tab → Edit the existing origin → change "Origin domain" to the Function URL's hostname (`<function-url-id>.lambda-url.us-east-2.on.aws`, no `https://` prefix, no path) → keep protocol HTTPS-only, keep the same cache/origin-request policies. Save.

- [ ] **Step 3: Verify end-to-end via the real custom domain**

```bash
curl -s https://nj-bioenergy-api.apps.qsdsan.com/health
curl -s "https://nj-bioenergy-api.apps.qsdsan.com/api/v1/htl/calc?kg_hr=150"
```

Run each of these **5-10 times in a row** (not just once) — you want to see both a cold-start response and subsequent warm ones, since that variance is exactly what the old ECS/ALB setup didn't have and what you're trading for the cost savings. Confirm the frontend (`nj-bioenergy.apps.qsdsan.com`) still works end-to-end in a browser, including a real HTL calculation through the UI.

---

### Task 8 (AWS runbook — human-executed): Burn-in and decommission

**Files:**
- Modify: `deployments/qsdsan.md` (in the separate `deployments` repo, not this one) — update the backend section once this is live.

- [ ] **Step 1: Watch CloudWatch Logs/metrics for the Lambda function for a few days**

Console: CloudWatch → Log groups → `/aws/lambda/nj-bioenergy-api`. Watch for errors, and check the Lambda function's own Duration/Errors/Throttles metrics (Monitor tab) to confirm nothing is timing out or erroring under real traffic.

- [ ] **Step 2: Pause the old ECS service (don't delete yet)**

Console: ECS → the `nj-bioenergy-api-9c5e` service → Update service → set desired task count to **0**. This stops the ECS/vCPU-hour billing immediately while keeping the service/task-definition/ALB/target-group configuration intact for rollback.

- [ ] **Step 3: After a burn-in period you're comfortable with, delete the paused resources**

Once confident: delete the ECS service, the ALB, and (if nothing else in the VPC needs it) the NAT Gateway — in that order, checking `costs.csv`-style Cost Explorer exports the following month to confirm the ECS/ELB/VPC line items have actually dropped to near zero.

- [ ] **Step 4: Update the deployment inventory**

Edit `deployments/qsdsan.md`'s "Backend (API)" section to describe the Lambda + Function URL setup in place of ECS Express Mode, and add a line to its rotation/change log noting the cutover date. This is the doc referenced by `[[project_webapp_redeploy]]` — keep it as the source of truth for whoever touches this next.
