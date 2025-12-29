# Fixing Permission Errors

You're getting this error because the project exists but you don't have sufficient permissions.

## Quick Fix (Option 1: Use Existing Project with Permissions)

```bash
# List projects you have access to
gcloud projects list

# Use one of YOUR existing projects instead
export PROJECT_ID="YOUR-EXISTING-PROJECT-ID"
gcloud config set project $PROJECT_ID

# Then re-run the deploy script
./DEPLOY_QUICK.sh
```

## Option 2: Get Permissions on alphatest-prod

If you own the project but don't have permissions:

```bash
# Add yourself as owner
gcloud projects add-iam-policy-binding alphatest-prod \
  --member="user:velasabelo.com@gmail.com" \
  --role="roles/owner"
```

## Option 3: Create New Project with Different Name

```bash
# Create with a unique name
export PROJECT_ID="alphatest-$(date +%s)"
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Enable billing (REQUIRED)
# Get billing account ID
gcloud billing accounts list

# Link billing
gcloud billing projects link $PROJECT_ID \
  --billing-account=YOUR-BILLING-ACCOUNT-ID

# Now re-run deploy script
./DEPLOY_QUICK.sh
```

## Most Common Issue: Billing Not Enabled

```bash
# Check if billing is enabled
gcloud billing projects describe $PROJECT_ID

# If not enabled, link billing account
gcloud billing accounts list
gcloud billing projects link $PROJECT_ID --billing-account=ACCOUNT-ID
```

## Manual Deploy (If Script Fails)

```bash
# 1. Set project
gcloud config set project alphatest-prod

# 2. Enable billing FIRST (in console or CLI)
gcloud billing projects link alphatest-prod --billing-account=YOUR-BILLING-ACCOUNT

# 3. Enable APIs one by one
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com

# 4. Create secrets
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > /tmp/secret.txt
cat /tmp/secret.txt | gcloud secrets create secret-key --data-file=-

echo -n "YOUR-API-KEY" | gcloud secrets create anthropic-api-key --data-file=-

# 5. Deploy
gcloud run deploy alphatest \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --set-secrets="SECRET_KEY=secret-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest"
```
