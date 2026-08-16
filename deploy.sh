#!/usr/bin/env bash
# Deploys the orchestrator + four worker agents to Google Cloud Run, each as its
# own service with its own service account (this is what makes the
# zero-trust boundary real rather than a config file).
#
# Prereqs:
#   gcloud auth login
#   gcloud config set project YOUR_PROJECT_ID
#   gcloud services enable run.googleapis.com firestore.googleapis.com \
#       pubsub.googleapis.com aiplatform.googleapis.com
#   gcloud firestore databases create --location=us-central1 (if not already)
#
set -euo pipefail

PROJECT_ID="$(gcloud config get-value project)"
REGION="us-central1"

echo "Deploying to project: $PROJECT_ID in $REGION"

# --- Service accounts, one per agent, minimal roles ------------------------
for sa in report-agent-sa db-query-agent-sa notifier-agent-sa security-auditor-sa orchestrator-sa; do
  gcloud iam service-accounts create "$sa" --display-name="$sa" || true
done

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:report-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:db-query-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.viewer"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:security-auditor-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.viewer"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:orchestrator-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:orchestrator-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# --- Build + deploy worker agents (same image, different env vars) ---------
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/agent-worker" -f agents/Dockerfile .

deploy_worker () {
  local name=$1 module=$2 class=$3 sa=$4
  gcloud run deploy "$name" \
    --image "gcr.io/${PROJECT_ID}/agent-worker" \
    --region "$REGION" \
    --service-account "${sa}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --set-env-vars "WORKER_AGENT_MODULE=${module},WORKER_AGENT_CLASS=${class},GEMINI_API_KEY=${GEMINI_API_KEY:-}" \
    --no-allow-unauthenticated
}

deploy_worker "report-agent" "agents.report_agent.agent" "ReportAgent" "report-agent-sa"
deploy_worker "db-query-agent" "agents.db_query_agent.agent" "DbQueryAgent" "db-query-agent-sa"
deploy_worker "notifier-agent" "agents.notifier_agent.agent" "NotifierAgent" "notifier-agent-sa"
deploy_worker "security-auditor-agent" "agents.security_auditor_agent.agent" "SecurityAuditorAgent" "security-auditor-sa"

# --- Build + deploy orchestrator --------------------------------------------
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/orchestrator" -f orchestrator/Dockerfile .

gcloud run deploy "orchestrator" \
  --image "gcr.io/${PROJECT_ID}/orchestrator" \
  --region "$REGION" \
  --service-account "orchestrator-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GEMINI_API_KEY=${GEMINI_API_KEY:-}" \
  --allow-unauthenticated

echo "Done. Orchestrator Control Plane URL:"
gcloud run services describe orchestrator --region "$REGION" --format="value(status.url)"
