# AlphaTest Production Deployment Guide

Complete guide to deploy AlphaTest with database, security, and monitoring.

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Set your project ID
export PROJECT_ID="alphatest-prod"
export REGION="us-central1"

# 2. Create project and enable services
gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com secretmanager.googleapis.com

# 3. Create secrets
echo -n "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" | gcloud secrets create secret-key --data-file=-
echo -n "YOUR_ANTHROPIC_API_KEY_HERE" | gcloud secrets create anthropic-api-key --data-file=-

# 4. Deploy
gcloud run deploy alphatest \
  --source . \
  --region=$REGION \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=10 \
  --set-secrets="SECRET_KEY=secret-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest"

# 5. Get your URL
gcloud run services describe alphatest --region=$REGION --format="value(status.url)"
```

**Done! Your AlphaTest is now live.** 🎉

---

## 📋 Table of Contents

1. [Database Setup](#database-setup)
2. [Security Configuration](#security-configuration)
3. [Production Deployment](#production-deployment)
4. [Custom Domain](#custom-domain)
5. [Monitoring](#monitoring)

---

## 💾 Database Setup

### Option A: Firestore (Recommended)

**Best for:** Quick setup, serverless, auto-scaling  
**Cost:** Free tier (1GB storage, 50K reads/day)

```bash
gcloud firestore databases create --region=$REGION
```

### Option B: Cloud SQL PostgreSQL

**Best for:** Complex queries, relational data  
**Cost:** ~$7/month (db-f1-micro)

```bash
gcloud sql instances create alphatest-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --root-password=SECURE_PASSWORD

gcloud sql databases create alphatest --instance=alphatest-db
gcloud sql users create appuser --instance=alphatest-db --password=APP_PASSWORD
```

---

## 🔒 Security Configuration

### 1. Generate Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Store in Secret Manager

```bash
# Secret key
echo -n "YOUR_GENERATED_KEY" | gcloud secrets create secret-key --data-file=-

# Anthropic API key
echo -n "sk-ant-YOUR-KEY" | gcloud secrets create anthropic-api-key --data-file=-
```

### 3. Grant Access

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding secret-key \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:$PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 🌐 Production Deployment

### Deploy with gcloud

```bash
gcloud run deploy alphatest \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --max-instances=10 \
  --min-instances=0 \
  --set-secrets="SECRET_KEY=secret-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --set-env-vars="ENV=production,CORS_ALLOWED_ORIGINS=*"
```

### Deploy with Cloud Build

```bash
gcloud builds submit --config=cloudbuild.yaml
```

---

## 🌍 Custom Domain

### 1. Verify Domain

```bash
gcloud domains verify yourdomain.com
```

### 2. Map Domain

```bash
gcloud run domain-mappings create \
  --service=alphatest \
  --domain=app.yourdomain.com \
  --region=us-central1
```

### 3. Configure DNS

Add CNAME record in your DNS provider:

```
Type: CNAME
Name: app
Value: ghs.googlehosted.com
```

SSL certificate is provisioned automatically (15-60 minutes).

---

## 📊 Monitoring

### View Logs

```bash
# Real-time logs
gcloud run services logs tail alphatest --region=us-central1

# Last 50 logs
gcloud run services logs read alphatest --limit=50
```

### Cloud Console

- Logs: https://console.cloud.google.com/logs
- Metrics: https://console.cloud.google.com/run
- Errors: https://console.cloud.google.com/errors

---

## ✅ Production Checklist

### Security
- [ ] Generate new SECRET_KEY (not the default)
- [ ] Store secrets in Secret Manager
- [ ] Set CORS to your actual domain
- [ ] Enable Cloud Armor (DDoS protection)
- [ ] Review IAM permissions

### Database
- [ ] Choose database type
- [ ] Enable automated backups
- [ ] Test restore process
- [ ] Configure monitoring

### Performance
- [ ] Set appropriate memory/CPU
- [ ] Configure auto-scaling
- [ ] Enable Cloud CDN
- [ ] Test under load

### Monitoring
- [ ] Set up error alerts
- [ ] Configure uptime monitoring
- [ ] Set budget alerts
- [ ] Enable Cloud Trace

---

## 💰 Cost Estimate

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud Run | 2GB RAM, low traffic | $5-15 |
| Firestore | Free tier | $0 |
| Cloud SQL | db-f1-micro | $7 |
| Secrets Manager | 3 secrets | $0.18 |
| **Total** | | **$12-22/month** |

**Free tier includes:**
- Cloud Run: 2M requests/month
- Firestore: 1GB storage, 50K reads/day
- Secret Manager: 6 free secrets

---

## 🐛 Troubleshooting

### Service won't start

```bash
gcloud run services logs read alphatest --region=us-central1 --limit=50
```

### High costs

```bash
# Reduce max instances
gcloud run services update alphatest --max-instances=5 --region=us-central1
```

### Database connection issues

```bash
# Check connection
gcloud sql instances describe alphatest-db
```

---

## 📚 Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Anthropic API Docs](https://docs.anthropic.com/)

---

## 🆘 Support

Issues? Check:
1. Cloud Run logs in Console
2. Secret Manager permissions
3. API key validity
4. Resource quotas

---

**Your AlphaTest is now production-ready!** 🎊
