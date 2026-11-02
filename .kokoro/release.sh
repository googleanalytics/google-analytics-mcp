#!/bin/bash
set -euo pipefail

# Default to dry-run for safety unless DRY_RUN=false is explicitly passed.
DRY_RUN="${DRY_RUN:-true}"
if [[ "${DRY_RUN}" != "true" && "${DRY_RUN}" != "false" ]]; then
  echo "ERROR: DRY_RUN must be 'true' or 'false' (got '${DRY_RUN}')." >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# 1. Workspace & Directory Resolution
# -----------------------------------------------------------------------------
# Navigate to the root of the repository
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

echo "=== Building and Releasing from: ${REPO_DIR} (DRY_RUN=${DRY_RUN}) ==="

# -----------------------------------------------------------------------------
# 2. Environment & Tooling Setup
# -----------------------------------------------------------------------------
PYENV_VER="3.12"

echo "=== Installing pyenv Python version (if needed): ${PYENV_VER} ==="
pyenv install -s "${PYENV_VER}"

echo "=== Activating pyenv Python version: ${PYENV_VER} ==="
pyenv global "${PYENV_VER}"

# Setup virtual environment for releasing
python3 -m venv .venv
source ./.venv/bin/activate

# Install standard Python build and packaging tools
python3 -m pip install --require-hashes -r .kokoro/requirements.txt

# -----------------------------------------------------------------------------
# 3. Clean and Build Distribution Packages
# -----------------------------------------------------------------------------
echo "=== Cleaning previous build artifacts ==="
rm -rf dist/ build/ *.egg-info

echo "=== Building sdist and wheel ==="
python3 -m build

echo "=== Validating built packages with twine ==="
twine --version
twine check dist/*

# -----------------------------------------------------------------------------
# 4. Upload to Internal Exit Gate Artifact Registry
# -----------------------------------------------------------------------------
EXIT_GATE_PROJECT="oss-exit-gate-prod"
EXIT_GATE_LOCATION="us"
EXIT_GATE_REPOSITORY="measurement-devrel--pypi"
PACKAGE_NAME="analytics-mcp"

# Delete existing package from the Exit Gate staging repository if present.
# This prevents twine upload failures on retries or re-releases of the same version.
if gcloud artifacts packages describe "${PACKAGE_NAME}" \
    --project="${EXIT_GATE_PROJECT}" \
    --location="${EXIT_GATE_LOCATION}" \
    --repository="${EXIT_GATE_REPOSITORY}" &>/dev/null; then
  echo "=== Deleting existing package '${PACKAGE_NAME}' from Exit Gate staging repository ==="
  gcloud artifacts packages delete "${PACKAGE_NAME}" \
    --project="${EXIT_GATE_PROJECT}" \
    --location="${EXIT_GATE_LOCATION}" \
    --repository="${EXIT_GATE_REPOSITORY}" \
    --quiet
else
  echo "=== Skipping deletion. Package '${PACKAGE_NAME}' not found in staging repository. This is normal. 🙂 ==="
fi

# keyrings.google-artifactregistry-auth automatically handles authentication
# using the ambient Kokoro BYOSA Service Account.
EXIT_GATE_REPO="https://us-python.pkg.dev/oss-exit-gate-prod/measurement-devrel--pypi"

echo "=== Uploading packages to Exit Gate staging repository: ${EXIT_GATE_REPO} ==="
twine upload --repository-url "${EXIT_GATE_REPO}" dist/*

# -----------------------------------------------------------------------------
# 5. Trigger Exit Gate Release via GCS Manifest
# -----------------------------------------------------------------------------
# If DRY_RUN is set to "true", stop here so you can verify the AR staging
# without publishing to public PyPI.
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "=== DRY_RUN is enabled. Skipping manifest upload to Exit Gate. ==="
  echo "Artifacts are staged in Artifact Registry."
  exit 0
fi

echo "=== Creating targeted release manifest for analytics-mcp ==="
cat <<EOF > manifest.json
{
  "publish_all": false,
  "publishing_groups": [
    {
      "packages": [
        {
          "name": "analytics-mcp"
        }
      ]
    }
  ]
}
EOF

EXIT_GATE_BUCKET="gs://oss-exit-gate-prod-projects-bucket/measurement-devrel/pypi/manifests"
MANIFEST_NAME="manifest-$(date +%Y%m%d%H%M%S).json"

echo "=== Uploading manifest to ${EXIT_GATE_BUCKET}/${MANIFEST_NAME} ==="
gcloud storage cp manifest.json "${EXIT_GATE_BUCKET}/${MANIFEST_NAME}"

echo "========================================================================="
echo "Release successfully triggered! Exit Gate will now verify BCID and publish to PyPI."
echo "========================================================================="
