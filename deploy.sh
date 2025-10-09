#!/usr/bin/env bash
set -euo pipefail

# === Configuration ===
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
APP_NAME="analytics-mcp-server"
IMAGE_TAG="${APP_NAME}:${TIMESTAMP}"
RESOURCE_GROUP="adaly-dev"
LOCATION="eastus2"
ACR_NAME="adalyacrdev"
KEY_VAULT_NAME="adaly-keyvault-dev"

# Container Apps Configuration
CONTAINER_APP_NAME="${APP_NAME}"
CONTAINER_APP_ENV_NAME="adaly-container-environment-dev"
CPU_CORES="0.5"
MEMORY="1Gi"
MIN_REPLICAS="1"
MAX_REPLICAS="3"
TARGET_PORT="8080"

# Full image name
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
IMAGE_NAME="$ACR_LOGIN_SERVER/$IMAGE_TAG"

# Key Vault URLs
KEY_VAULT_URI="https://${KEY_VAULT_NAME}.vault.azure.net"

echo "Starting deployment of Python UV project to Azure Container Apps..."
echo "Configuration:"
echo "  App Name: $CONTAINER_APP_NAME"
echo "  Image: $IMAGE_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  Key Vault: $KEY_VAULT_NAME"

# === Azure Login ===
echo ""
echo "Checking Azure login..."
az account show >/dev/null 2>&1 || {
    echo "Not logged into Azure. Please run 'az login' first."
    exit 1
}

# === Build & Push using ACR Tasks ===
echo ""
echo "Building & pushing image with ACR..."
az acr build \
    --registry $ACR_NAME \
    --image $IMAGE_TAG \
    --file Dockerfile \
    .

echo "✓ Image built and pushed to ACR"

# === Check if Container Apps environment exists ===
echo ""
echo "Checking Container Apps environment..."
if ! az containerapp env show --name $CONTAINER_APP_ENV_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "Creating Container Apps environment..."
    az containerapp env create \
        --name $CONTAINER_APP_ENV_NAME \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION
    echo "✓ Container Apps environment created"
else
    echo "✓ Container Apps environment exists"
fi

# === Check if Container App exists (update vs create) ===
echo ""
echo "Checking if Container App exists..."

APP_EXISTS=false
if az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    APP_EXISTS=true
fi

if [ "$APP_EXISTS" = true ]; then
    echo "Updating existing Container App..."
    az containerapp update \
        --name $CONTAINER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $IMAGE_NAME \
        --cpu $CPU_CORES \
        --memory $MEMORY \
        --min-replicas $MIN_REPLICAS \
        --max-replicas $MAX_REPLICAS \
        --set-env-vars \
            "PYTHONPATH=/app" \
            "UV_PROJECT_ENVIRONMENT=.venv" \
            "GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account-key.json" \
        --replace-env-vars \
            "AZURE_TENANT_ID=secretref:ga4mcp-auth-azure-tenant-id" \
            "AZURE_CLIENT_ID=secretref:ga4mcp-auth-azure-client-id" \
            "AZURE_CLIENT_SECRET=secretref:ga4mcp-auth-azure-client-secret" \
            "GOOGLE_SERVICE_ACCOUNT_KEY_JSON=secretref:google-service-account-key-json" \
        --secrets \
            "ga4mcp-auth-azure-tenant-id=keyvaultref:${KEY_VAULT_URI}/secrets/ga4mcp-auth-azure-tenant-id,identityref:system" \
            "ga4mcp-auth-azure-client-id=keyvaultref:${KEY_VAULT_URI}/secrets/ga4mcp-auth-azure-client-id,identityref:system" \
            "ga4mcp-auth-azure-client-secret=keyvaultref:${KEY_VAULT_URI}/secrets/ga4mcp-auth-azure-client-secret,identityref:system" \
            "google-service-account-key-json=keyvaultref:${KEY_VAULT_URI}/secrets/google-service-account-key-json,identityref:system"
    
    echo "✓ Container App updated"
else
    echo "Creating new Container App with system-assigned managed identity..."
    az containerapp create \
        --name $CONTAINER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $CONTAINER_APP_ENV_NAME \
        --image $IMAGE_NAME \
        --cpu $CPU_CORES \
        --memory $MEMORY \
        --min-replicas $MIN_REPLICAS \
        --max-replicas $MAX_REPLICAS \
        --target-port $TARGET_PORT \
        --ingress 'external' \
        --registry-server $ACR_LOGIN_SERVER \
        --system-assigned \
        --env-vars \
            "PYTHONPATH=/app" \
            "UV_PROJECT_ENVIRONMENT=.venv" \
            "GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/service-account-key.json" \
            "AZURE_TENANT_ID=secretref:ga4mcp-auth-azure-tenant-id" \
            "AZURE_CLIENT_ID=secretref:ga4mcp-auth-azure-client-id" \
            "AZURE_CLIENT_SECRET=secretref:ga4mcp-auth-azure-client-secret" \
            "GOOGLE_SERVICE_ACCOUNT_KEY_JSON=secretref:google-service-account-key-json" \
        --secrets \
            "ga4mcp-auth-azure-tenant-id=keyvaultref:${KEY_VAULT_URI}/secrets/ga4mcp-auth-azure-tenant-id,identityref:system" \
            "ga4mcp-auth-azure-client-id=keyvaultref:${KEY_VAULT_URI}/secrets/ga4mcp-auth-azure-client-id,identityref:system" \
            "ga4mcp-auth-azure-client-secret=keyvaultref:${KEY_VAULT_URI}/secrets/ga4mcp-auth-azure-client-secret,identityref:system" \
            "google-service-account-key-json=keyvaultref:${KEY_VAULT_URI}/secrets/google-service-account-key-json,identityref:system"
    
    echo "✓ Container App created"
fi

# === Grant Key Vault Access to Container App ===
echo ""
echo "Configuring Key Vault access..."

# Get the managed identity principal ID
PRINCIPAL_ID=$(az containerapp show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query identity.principalId \
    --output tsv)

if [ -z "$PRINCIPAL_ID" ] || [ "$PRINCIPAL_ID" = "null" ]; then
    echo "Warning: Could not retrieve managed identity. Enabling system-assigned identity..."
    az containerapp identity assign \
        --name $CONTAINER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --system-assigned
    
    # Retrieve the principal ID again
    PRINCIPAL_ID=$(az containerapp show \
        --name $CONTAINER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --query identity.principalId \
        --output tsv)
fi

echo "  Managed Identity Principal ID: $PRINCIPAL_ID"

# Grant Key Vault access
echo "  Granting Key Vault secret permissions..."
az keyvault set-policy \
    --name $KEY_VAULT_NAME \
    --object-id $PRINCIPAL_ID \
    --secret-permissions get list \
    >/dev/null

echo "✓ Key Vault access configured"

# === Get the application URL ===
echo ""
echo "Getting application URL..."
APP_URL=$(az containerapp show \
    --name $CONTAINER_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn \
    --output tsv)

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✓ Deployment Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Application URL: https://$APP_URL"
echo ""
echo "Useful Commands:"
echo "  Monitor logs:"
echo "    az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "  View in Azure Portal:"
echo "    https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id --output tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_APP_NAME"
echo ""
echo "  Check secret configuration:"
echo "    az containerapp secret list --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "════════════════════════════════════════════════════════════════"

echo ""
echo "Deployment script finished successfully!"



ga4mcp-auth-azure-tenant-id
ga4mcp-auth-azure-client-secret
ga4mcp-auth-azure-client-id