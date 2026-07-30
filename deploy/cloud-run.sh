#!/usr/bin/env bash

# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Two-phase Cloud Run deployment for the Google Analytics MCP server.
#
# Phase 1 deploys the service so Cloud Run assigns its URL. Phase 2 updates
# the service with ANALYTICS_MCP_BASE_URL set to that URL, which the OAuth
# provider needs to build its redirect URI.
#
# Required environment variables:
#   PROJECT_ID       Google Cloud project ID
#   REGION           Cloud Run region (e.g. us-central1)
#   OAUTH_CLIENT_ID  OAuth 2.0 web client ID
#
# Optional environment variables:
#   SERVICE_NAME     Cloud Run service name (default: analytics-mcp)
#   ARTIFACT_REPO    Artifact Registry repo name (default: analytics-mcp)
#   SECRET_NAME      Secret Manager secret holding the OAuth client secret
#                    (default: analytics-mcp-oauth-client-secret)
#
# Prerequisites (see README "Remote deployment" section):
#   - gcloud authenticated against PROJECT_ID
#   - OAuth client created, client secret stored in Secret Manager
#   - Cloud Run, Cloud Build, Artifact Registry, Secret Manager APIs enabled

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project ID}"
: "${REGION:?Set REGION to the Cloud Run region, e.g. us-central1}"
: "${OAUTH_CLIENT_ID:?Set OAUTH_CLIENT_ID to your OAuth 2.0 web client ID}"

SERVICE_NAME="${SERVICE_NAME:-analytics-mcp}"
ARTIFACT_REPO="${ARTIFACT_REPO:-analytics-mcp}"
SECRET_NAME="${SECRET_NAME:-analytics-mcp-oauth-client-secret}"

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/analytics-mcp:latest"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! gcloud artifacts repositories describe "${ARTIFACT_REPO}" \
  --project "${PROJECT_ID}" --location "${REGION}" >/dev/null 2>&1; then
  echo ">> Creating Artifact Registry repository '${ARTIFACT_REPO}'"
  gcloud artifacts repositories create "${ARTIFACT_REPO}" \
    --project "${PROJECT_ID}" \
    --location "${REGION}" \
    --repository-format docker
fi

echo ">> Building image with Cloud Build: ${IMAGE}"
gcloud builds submit "${REPO_ROOT}" \
  --project "${PROJECT_ID}" \
  --tag "${IMAGE}"

echo ">> Phase 1: deploying ${SERVICE_NAME} to discover the service URL"
# --allow-unauthenticated is intentional: authentication happens at the
# application layer. The OAuth provider rejects requests to /mcp that don't
# carry a valid per-user token.
gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${IMAGE}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ANALYTICS_MCP_OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}" \
  --set-secrets "ANALYTICS_MCP_OAUTH_CLIENT_SECRET=${SECRET_NAME}:latest"

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --format 'value(status.url)')"

echo ">> Phase 2: setting ANALYTICS_MCP_BASE_URL=${SERVICE_URL}"
gcloud run services update "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --update-env-vars "ANALYTICS_MCP_BASE_URL=${SERVICE_URL}"

cat <<EOF

Deployment complete.

  Service URL:  ${SERVICE_URL}
  MCP endpoint: ${SERVICE_URL}/mcp

Next steps:
  1. Add this authorized redirect URI to your OAuth client
     (https://console.cloud.google.com/apis/credentials):

       ${SERVICE_URL}/auth/callback

  2. Connect from claude.ai (Settings -> Connectors) using:

       ${SERVICE_URL}/mcp
EOF
