#!/bin/bash
# AlphaTest Quick Deploy Script
# Run this to deploy AlphaTest to Google Cloud Run

set -e

echo "🚀 AlphaTest Deployment Script"
echo "================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
read -p "Enter your GCP Project ID (or press Enter for 'alphatest-prod'): " PROJECT_ID
PROJECT_ID=${PROJECT_ID:-alphatest-prod}

# Get region
read -p "Enter region (or press Enter for 'us-central1'): " REGION
REGION=${REGION:-us-central1}

# Get Anthropic API key
read -p "Enter your Anthropic API key: " ANTHROPIC_KEY

if [ -z "$ANTHROPIC_KEY" ]; then
    echo "❌ Anthropic API key is required"
    exit 1
fi

echo ""
echo "📋 Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo ""

# Set project
echo "1️⃣ Setting up GCP project..."
gcloud config set project $PROJECT_ID 2>/dev/null || {
    echo "Creating new project..."
    gcloud projects create $PROJECT_ID
    gcloud config set project $PROJECT_ID
}

# Enable services
echo "2️⃣ Enabling required services..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  firestore.googleapis.com

# Generate secret key
echo "3️⃣ Generating secret key..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Create secrets
echo "4️⃣ Creating secrets..."
echo -n "$SECRET_KEY" | gcloud secrets create secret-key --data-file=- 2>/dev/null || {
    echo "Secret already exists, updating..."
    echo -n "$SECRET_KEY" | gcloud secrets versions add secret-key --data-file=-
}

echo -n "$ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key --data-file=- 2>/dev/null || {
    echo "API key secret already exists, updating..."
    echo -n "$ANTHROPIC_KEY" | gcloud secrets versions add anthropic-api-key --data-file=-
}

# Grant permissions
echo "5️⃣ Setting up permissions..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding secret-key \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" > /dev/null 2>&1 || true

gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" > /dev/null 2>&1 || true

# Deploy
echo "6️⃣ Deploying to Cloud Run..."
gcloud run deploy alphatest \
  --source . \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --max-instances=10 \
  --min-instances=0 \
  --set-secrets="SECRET_KEY=secret-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --set-env-vars="ENV=production,CORS_ALLOWED_ORIGINS=*"

# Get URL
echo ""
echo "✅ Deployment complete!"
echo ""
SERVICE_URL=$(gcloud run services describe alphatest --region=$REGION --format="value(status.url)")
echo "🌐 Your AlphaTest is live at:"
echo "   $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "   1. Visit the URL above to test your deployment"
echo "   2. Set up a custom domain (optional)"
echo "   3. Configure monitoring and alerts"
echo ""
echo "📚 Full documentation: DEPLOYMENT_PRODUCTION.md"
