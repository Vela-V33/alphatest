# Deploying AlphaTest to Google Cloud Platform

This guide walks you through deploying AlphaTest as a public website on Google Cloud Platform using Cloud Run.

## Prerequisites

1. **Google Cloud Account**: Create one at https://cloud.google.com
2. **Google Cloud SDK**: Install from https://cloud.google.com/sdk/docs/install
3. **Anthropic API Key**: Get from https://console.anthropic.com/

## Cost Estimate

Cloud Run pricing is pay-as-you-go:
- **Free tier**: 2 million requests/month, 360,000 GB-seconds/month
- **Typical cost**: $5-20/month for small to medium usage
- **Browser automation**: Uses 2GB RAM, will consume more resources

## Quick Deploy (5 Minutes)

### Step 1: Set Up GCP Project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create alphatest-prod --name="AlphaTest Production"

# Set the project
gcloud config set project alphatest-prod

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 2: Set Environment Variables

Create a file called `env.yaml` with your configuration:

```yaml
ENV: production
SECRET_KEY: "CHANGE-THIS-TO-A-RANDOM-SECRET-STRING"
ANTHROPIC_API_KEY: "sk-ant-your-api-key-here"
CORS_ALLOWED_ORIGINS: "*"
```

**IMPORTANT**: Generate a secure SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Deploy to Cloud Run

```bash
# Build and deploy in one command
gcloud run deploy alphatest \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --concurrency 80 \
  --max-instances 10 \
  --env-vars-file env.yaml
```

This will:
- Build the Docker container
- Push to Google Container Registry
- Deploy to Cloud Run
- Give you a public URL like: `https://alphatest-xxxxx-uc.a.run.app`

### Step 4: Access Your Website

Once deployment completes, you'll see:
```
Service [alphatest] revision [alphatest-00001-xxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://alphatest-xxxxx-uc.a.run.app
```

Visit that URL in your browser!

## Advanced Deployment Options

### Option 1: Manual Docker Build

If you prefer more control:

```bash
# Build the Docker image
docker build -t gcr.io/alphatest-prod/alphatest:latest .

# Push to Container Registry
docker push gcr.io/alphatest-prod/alphatest:latest

# Deploy to Cloud Run
gcloud run deploy alphatest \
  --image gcr.io/alphatest-prod/alphatest:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --env-vars-file env.yaml
```

### Option 2: Automated CI/CD with Cloud Build

Set up automatic deployments from GitHub:

1. **Connect your repository**:
```bash
gcloud beta builds triggers create github \
  --repo-name=alphatest \
  --repo-owner=YOUR_GITHUB_USERNAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

2. **Set Cloud Build environment variables**:
   - Go to Cloud Console → Cloud Build → Settings
   - Add your secret environment variables (ANTHROPIC_API_KEY, SECRET_KEY)

3. **Push to GitHub**: Every push to main branch will auto-deploy!

### Option 3: Custom Domain

Map your own domain to Cloud Run:

```bash
# Verify domain ownership first in GCP Console
gcloud run domain-mappings create \
  --service alphatest \
  --domain app.yourdomain.com \
  --region us-central1
```

Then add the DNS records shown in the output to your domain provider.

## Environment Variables Reference

Set these in Cloud Run:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ENV` | Yes | Environment mode | `production` |
| `SECRET_KEY` | Yes | Flask secret key | Random 32+ char string |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key | `sk-ant-...` |
| `CORS_ALLOWED_ORIGINS` | No | Allowed CORS origins | `*` or `https://yourdomain.com` |
| `PORT` | Auto | Server port (set by Cloud Run) | `8080` |
| `ANTHROPIC_MODEL` | No | Claude model to use | `claude-sonnet-4-20250514` |

### Setting Environment Variables After Deployment

```bash
gcloud run services update alphatest \
  --region us-central1 \
  --update-env-vars SECRET_KEY=your-new-secret-key
```

## Persistent Storage

By default, Cloud Run is stateless. For persistent data/reports, you have options:

### Option 1: Cloud Storage (Recommended)

Store projects and reports in Google Cloud Storage:

```bash
# Create buckets
gsutil mb gs://alphatest-data
gsutil mb gs://alphatest-reports

# Set permissions
gsutil iam ch allUsers:objectViewer gs://alphatest-reports
```

You'll need to modify `server.py` to use Cloud Storage SDK instead of local filesystem.

### Option 2: Cloud SQL

For a production database:

```bash
# Create PostgreSQL instance
gcloud sql instances create alphatest-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create alphatest --instance=alphatest-db
```

## Security Hardening

### 1. Require Authentication

```bash
# Deploy with authentication required
gcloud run deploy alphatest \
  --no-allow-unauthenticated \
  --region us-central1
```

Then use Cloud IAM to manage access.

### 2. Set Up Cloud Armor

Protect against DDoS and add IP filtering:

```bash
# Create security policy
gcloud compute security-policies create alphatest-policy \
  --description "AlphaTest WAF policy"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy alphatest-policy \
  --expression "true" \
  --action "rate-based-ban" \
  --rate-limit-threshold-count 100 \
  --rate-limit-threshold-interval-sec 60
```

### 3. Restrict CORS

Update your `env.yaml`:

```yaml
CORS_ALLOWED_ORIGINS: "https://yourdomain.com,https://app.yourdomain.com"
```

### 4. Set Up HTTPS

Cloud Run automatically provides HTTPS with valid SSL certificates.

## Monitoring and Logging

### View Logs

```bash
# Real-time logs
gcloud run services logs tail alphatest --region us-central1

# Recent logs
gcloud run services logs read alphatest --region us-central1 --limit 50
```

### Cloud Monitoring

View metrics in GCP Console:
- Cloud Run → alphatest → Metrics
- See request count, latency, CPU, memory usage

### Set Up Alerts

```bash
# Example: Alert on high error rate
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="AlphaTest High Error Rate" \
  --condition-threshold-value=10 \
  --condition-threshold-duration=300s
```

## Scaling Configuration

### Adjust Resources

```bash
# Increase memory and CPU
gcloud run services update alphatest \
  --memory 4Gi \
  --cpu 4 \
  --region us-central1
```

### Control Concurrency

```bash
# Process fewer requests per instance (better for CPU-intensive tasks)
gcloud run services update alphatest \
  --concurrency 10 \
  --region us-central1
```

### Set Instance Limits

```bash
# Control min/max instances
gcloud run services update alphatest \
  --min-instances 1 \
  --max-instances 20 \
  --region us-central1
```

## Cost Optimization

1. **Set max instances**: Prevent runaway costs
   ```bash
   gcloud run services update alphatest --max-instances 5
   ```

2. **Use minimum instances wisely**:
   - `--min-instances 0`: Cold starts but cheapest
   - `--min-instances 1`: Always warm, costs ~$10/month

3. **Set timeout**: Prevent long-running requests
   ```bash
   gcloud run services update alphatest --timeout 1800
   ```

4. **Monitor costs**: Set up billing alerts in GCP Console

## Troubleshooting

### Container fails to start

Check logs:
```bash
gcloud run services logs read alphatest --region us-central1 --limit 100
```

### Out of memory

Increase memory:
```bash
gcloud run services update alphatest --memory 4Gi --region us-central1
```

### Slow requests / Timeout

Increase CPU and timeout:
```bash
gcloud run services update alphatest \
  --cpu 4 \
  --timeout 3600 \
  --region us-central1
```

### Playwright browser won't start

The Dockerfile includes all dependencies. If issues persist:
- Check Cloud Run logs for specific error
- Ensure using at least 2Gi memory
- Try building locally first: `docker build . -t test`

## Updating Your Deployment

### Deploy New Version

```bash
# From source
gcloud run deploy alphatest --source . --region us-central1

# Or rebuild Docker image
docker build -t gcr.io/alphatest-prod/alphatest:latest .
docker push gcr.io/alphatest-prod/alphatest:latest
gcloud run deploy alphatest \
  --image gcr.io/alphatest-prod/alphatest:latest \
  --region us-central1
```

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list --service alphatest --region us-central1

# Route traffic to specific revision
gcloud run services update-traffic alphatest \
  --to-revisions alphatest-00001-xxx=100 \
  --region us-central1
```

## Complete Example Commands

Here's everything in order:

```bash
# 1. Setup
gcloud auth login
gcloud projects create alphatest-prod --name="AlphaTest"
gcloud config set project alphatest-prod
gcloud services enable run.googleapis.com containerregistry.googleapis.com

# 2. Create env.yaml with your secrets
cat > env.yaml << EOF
ENV: production
SECRET_KEY: "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
ANTHROPIC_API_KEY: "sk-ant-your-key-here"
CORS_ALLOWED_ORIGINS: "*"
EOF

# 3. Deploy
gcloud run deploy alphatest \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 10 \
  --env-vars-file env.yaml

# 4. Done! Your URL will be shown
```

## Support

- **GCP Documentation**: https://cloud.google.com/run/docs
- **Cloud Run Pricing**: https://cloud.google.com/run/pricing
- **Anthropic API**: https://docs.anthropic.com/

## Next Steps

After deployment:

1. **Add Authentication**: Implement user management system
2. **Set Up Database**: Migrate to Cloud SQL for multi-user support
3. **Configure Cloud Storage**: Store reports in GCS
4. **Add Custom Domain**: Map your domain to the service
5. **Enable Cloud CDN**: Speed up static assets
6. **Set Up Backups**: Regular backups of user data
7. **Configure Monitoring**: Set up alerts and dashboards
