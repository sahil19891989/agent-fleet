# GCP Deployment Log — Fortified Enterprise Agent Fleet

A record of every step taken to stand this project up on Google Cloud, in order,
with the actual commands run. Useful both as a reproducibility record and as
evidence the backend genuinely runs on GCP.

- **Account**: sahilguglani1989@gmail.com
- **Project**: `project-6f1a71f3-6664-4281-822` ("My First Project", free trial, ₹28,693.88 credit / 90 days)
- **Region**: `us-central1`

## 1. Local tooling

```bash
winget install --id Google.CloudSDK -e
gcloud auth login
```
Opened a browser OAuth consent screen; authenticated as sahilguglani1989@gmail.com.

## 2. Project selection

The account had three pre-existing projects with **no billing account attached**
(`elite-frame-500606-s8`, `gen-lang-client-0781887760`, `project-1967e1cf-6092-48f6-8cb`).
Rather than attach billing to one of those, signed up for the Google Cloud free
trial directly from the console, which created a fresh project with billing
enabled out of the box:

```bash
gcloud config set project project-6f1a71f3-6664-4281-822
```

## 3. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project=project-6f1a71f3-6664-4281-822
```

## 4. Create the Firestore database (provenance chain backend)

```bash
gcloud firestore databases create --location=us-central1 --project=project-6f1a71f3-6664-4281-822
```
Created in Native mode, free tier.

## 5. Create per-agent IAM service accounts

```bash
for sa in report-agent-sa db-query-agent-sa notifier-agent-sa security-auditor-sa orchestrator-sa; do
  gcloud iam service-accounts create "$sa" --display-name="$sa" --project=project-6f1a71f3-6664-4281-822
done
```

## 6. Bind least-privilege IAM roles

```bash
gcloud projects add-iam-policy-binding project-6f1a71f3-6664-4281-822 \
  --member="serviceAccount:report-agent-sa@project-6f1a71f3-6664-4281-822.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding project-6f1a71f3-6664-4281-822 \
  --member="serviceAccount:db-query-agent-sa@project-6f1a71f3-6664-4281-822.iam.gserviceaccount.com" \
  --role="roles/cloudsql.viewer"

gcloud projects add-iam-policy-binding project-6f1a71f3-6664-4281-822 \
  --member="serviceAccount:security-auditor-sa@project-6f1a71f3-6664-4281-822.iam.gserviceaccount.com" \
  --role="roles/datastore.viewer"

gcloud projects add-iam-policy-binding project-6f1a71f3-6664-4281-822 \
  --member="serviceAccount:orchestrator-sa@project-6f1a71f3-6664-4281-822.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding project-6f1a71f3-6664-4281-822 \
  --member="serviceAccount:orchestrator-sa@project-6f1a71f3-6664-4281-822.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

## 7. Cost safety net

Set up budget alerts in Cloud Console (Billing → Budgets & alerts) before
spending any build/deploy time, since the project is on free-trial billing.

## 8. Secrets for the deployed environment

Generated a fresh random 64-char `PROVENANCE_SIGNING_SECRET` for the Cloud Run
deployment (not committed, not reused from local `.env`) — the HMAC chain's
security depends on this being unguessable, so the deployed instance gets its
own value rather than reusing the local dev placeholder.

## 9. Fix: `deploy.sh`'s `-f` flag doesn't work with `gcloud builds submit`

`gcloud builds submit --tag=X -f agents/Dockerfile .` is not valid —
`gcloud builds submit` has no `-f`/`--dockerfile` flag; it only auto-builds a
`Dockerfile` at the source root. Since `agents/Dockerfile` and
`orchestrator/Dockerfile` both need the **repo root** as build context (they
import from `firewall/`, `provenance/`, etc.) but aren't named `Dockerfile` at
that root, worked around it with small inline Cloud Build configs:

```yaml
# cloudbuild-worker.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'agents/Dockerfile', '-t', 'gcr.io/project-6f1a71f3-6664-4281-822/agent-worker', '.']
images:
  - 'gcr.io/project-6f1a71f3-6664-4281-822/agent-worker'
```
```bash
gcloud builds submit --config=cloudbuild-worker.yaml --project=project-6f1a71f3-6664-4281-822 .
```
(Same pattern for `orchestrator/Dockerfile` → `cloudbuild-orchestrator.yaml`.)

## 10. Fix: default Cloud Build service account lacked bucket read access

First build attempt failed:
```
ERROR: (gcloud.builds.submit) INVALID_ARGUMENT: could not resolve source:
googleapi: Error 403: 719825143579-compute@developer.gserviceaccount.com
does not have storage.objects.get access ...
```
This is a known gap on newly created projects — Cloud Build defaults to the
Compute Engine default service account, which isn't automatically granted
access to the auto-created `_cloudbuild` GCS bucket. Fixed with:
```bash
gcloud projects add-iam-policy-binding project-6f1a71f3-6664-4281-822 \
  --member="serviceAccount:719825143579-compute@developer.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"

gcloud projects add-iam-policy-binding project-6f1a71f3-6664-4281-822 \
  --member="serviceAccount:719825143579-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

## 11. Build the worker image

```bash
gcloud builds submit --config=cloudbuild-worker.yaml --project=project-6f1a71f3-6664-4281-822 .
```
**Result: SUCCESS.** `gcr.io/project-6f1a71f3-6664-4281-822/agent-worker:latest` built and pushed. Build ID `88d94328-c1db-46a2-adf8-c3a532989bef`, 1m16s.

## 12. Fix: `PubSubBus` was fire-and-forget, not a real request/response bus

`orchestrator/Dockerfile` set `BUS_BACKEND=pubsub` by default, but
`PubSubBus.send()` only publishes a message and returns
`{"status": "published", ...}` immediately — nothing subscribes to those
topics, so the orchestrator would never get a worker's actual output. That
would have made the deployed dashboard *look* like it was using the isolated
Cloud Run workers while actually returning fake placeholder results —
contradicting the project's core "isolated per-agent Cloud Run service"
claim. Fixed by adding a new `CloudRunHttpBus` to `orchestrator/bus.py` that
makes a genuine authenticated HTTPS call to each worker's Cloud Run URL
(ID token minted for the orchestrator's own service account via
`google.oauth2.id_token`), and switched the Dockerfile default to
`BUS_BACKEND=cloudrun`.

## 13. Fix: both Dockerfiles' CMD broke Python's import path

`CMD ["python", "agents/server.py"]` (and the orchestrator's equivalent) runs
the file as a script, which puts `/app/agents` — not `/app` — on
`sys.path[0]`, so `import agents.report_agent.agent` failed with
`ModuleNotFoundError: No module named 'agents'` at container startup (caught
via Cloud Run logs after the first worker deploy failed its startup probe).
Fixed both Dockerfiles to run as a module instead:
`CMD ["python", "-m", "agents.server"]` / `CMD ["python", "-m", "orchestrator.server"]`.

## 14. Rebuild worker image, deploy all 4 workers

```bash
gcloud builds submit --config=cloudbuild-worker.yaml --project=project-6f1a71f3-6664-4281-822 .
```
Then deployed each with `--no-allow-unauthenticated` and its own dedicated
service account:

| Service | Service Account | Deployed URL |
|---|---|---|
| `report-agent` | `report-agent-sa` | https://report-agent-719825143579.us-central1.run.app |
| `db-query-agent` | `db-query-agent-sa` | https://db-query-agent-719825143579.us-central1.run.app |
| `notifier-agent` | `notifier-agent-sa` | https://notifier-agent-719825143579.us-central1.run.app |
| `security-auditor-agent` | `security-auditor-sa` | https://security-auditor-agent-719825143579.us-central1.run.app |

## 15. Grant orchestrator-sa permission to call the workers

Each worker is private, so the orchestrator's own service account needs
explicit `roles/run.invoker` on each one:
```bash
for svc in report-agent db-query-agent notifier-agent security-auditor-agent; do
  gcloud run services add-iam-policy-binding $svc --region=us-central1 \
    --project=project-6f1a71f3-6664-4281-822 \
    --member="serviceAccount:orchestrator-sa@project-6f1a71f3-6664-4281-822.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
done
```

## 16. Build and deploy the orchestrator

```bash
gcloud builds submit --config=cloudbuild-orchestrator.yaml --project=project-6f1a71f3-6664-4281-822 .

gcloud run deploy orchestrator \
  --image gcr.io/project-6f1a71f3-6664-4281-822/orchestrator \
  --region us-central1 --project project-6f1a71f3-6664-4281-822 \
  --service-account orchestrator-sa@project-6f1a71f3-6664-4281-822.iam.gserviceaccount.com \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=...,GEMINI_API_KEY=...,GEMINI_MODEL=gemini-3.5-flash,GEMMA_MODEL=gemma-3-27b-it,PROVENANCE_SIGNING_SECRET=...,BUS_BACKEND=cloudrun,CHAIN_BACKEND=firestore,REPORT_AGENT_URL=...,DB_QUERY_AGENT_URL=...,NOTIFIER_AGENT_URL=...,SECURITY_AUDITOR_AGENT_URL=..." \
  --allow-unauthenticated
```
**Result: SUCCESS.** `https://orchestrator-719825143579.us-central1.run.app`

## 17. False alarm: `/healthz` specifically doesn't reach the container

Testing with `curl https://orchestrator-.../healthz` consistently returned a
generic Google-branded 404 with no `x-cloud-trace-context` header — meaning
that specific path never reaches Cloud Run's own request handling at all
(some edge-level behavior for that exact well-known path name). `/` and
`/api/fleet` both returned 200 with a real `server: Google Frontend` and
trace-context header the whole time, proving the deployment was actually
fine — `/healthz` was just the wrong path to test with from outside.

## 18. End-to-end verification

```bash
curl -X POST https://orchestrator-719825143579.us-central1.run.app/api/run-task \
  -H "Content-Type: application/json" -d '{"description":"Cloud deployment verification test"}'
```
**Result: `"status":"COMPLETED"`.** Real Gemini 3.5 calls through `db_query_agent`,
`report_agent`, and `notifier_agent` (10–12s latencies confirm live API calls,
not mocks), each running as its own isolated, IAM-scoped Cloud Run service,
invoked over authenticated HTTPS by the orchestrator's `CloudRunHttpBus`.

## Live URLs

- **Public dashboard**: https://orchestrator-719825143579.us-central1.run.app
- Workers (private, IAM-only): `report-agent`, `db-query-agent`, `notifier-agent`, `security-auditor-agent`
