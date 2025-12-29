# Migrating AlphaTest to Cloud Firestore

## Why Migrate?

**CRITICAL**: Your current JSON file storage (`data/users.json`, `data/projects.json`) is stored in Cloud Run's **ephemeral container storage**. This means:

- ❌ All user signups will be LOST on redeployment
- ❌ All projects will be LOST when container restarts
- ❌ All test reports will be LOST on scaling events

**Solution**: Migrate to Cloud Firestore for persistent, reliable data storage.

---

## Step 1: Enable Firestore (2 minutes)

```bash
# Set your project
gcloud config set project alphatest-482117

# Enable Firestore API
gcloud services enable firestore.googleapis.com

# Create Firestore database in Native mode
gcloud firestore databases create --location=us-central1 --type=firestore-native
```

**Note**: Choose the same region as your Cloud Run service (us-central1)

---

## Step 2: Install Firestore SDK

Update `requirements.txt`:

```txt
# Add this line to requirements.txt
google-cloud-firestore==2.14.0
```

Redeploy to install:
```bash
gcloud run deploy alphatest --source . --region=us-central1
```

---

## Step 3: Update Authentication Code

The updated `auth.py` will use Firestore instead of JSON files. Key changes:

**Before (JSON):**
```python
USERS_FILE = Path(__file__).parent / "data" / "users.json"

def load_users():
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    return {}
```

**After (Firestore):**
```python
from google.cloud import firestore
db = firestore.Client()

def load_users():
    users = {}
    docs = db.collection('users').stream()
    for doc in docs:
        users[doc.id] = doc.to_dict()
    return users
```

---

## Step 4: Update Project Storage

Similar changes for `server.py`:

**Before (JSON):**
```python
def load_projects():
    projects_file = DATA_DIR / "projects.json"
    if projects_file.exists():
        return json.loads(projects_file.read_text())
    return {}
```

**After (Firestore):**
```python
def load_projects():
    projects = {}
    docs = db.collection('projects').stream()
    for doc in docs:
        projects[doc.id] = doc.to_dict()
    return projects
```

---

## Step 5: Migrate Existing Data (if any)

If you have existing users/projects in JSON files that you want to keep:

```python
# migrate_to_firestore.py
from google.cloud import firestore
import json
from pathlib import Path

db = firestore.Client()

# Migrate users
users_file = Path("data/users.json")
if users_file.exists():
    users = json.loads(users_file.read_text())
    for email, user_data in users.items():
        db.collection('users').document(email).set(user_data)
    print(f"Migrated {len(users)} users")

# Migrate projects
projects_file = Path("data/projects.json")
if projects_file.exists():
    projects = json.loads(projects_file.read_text())
    for project_id, project_data in projects.items():
        db.collection('projects').document(project_id).set(project_data)
    print(f"Migrated {len(projects)} projects")
```

Run locally:
```bash
python migrate_to_firestore.py
```

---

## Step 6: Handle Report Storage

For test reports (HTML files), you have two options:

### Option A: Store in Cloud Storage (Recommended)
```bash
# Create storage bucket
gsutil mb -l us-central1 gs://alphatest-reports

# Make reports publicly readable
gsutil iam ch allUsers:objectViewer gs://alphatest-reports
```

Update code to upload reports:
```python
from google.cloud import storage

def save_report(report_html, report_id):
    storage_client = storage.Client()
    bucket = storage_client.bucket('alphatest-reports')
    blob = bucket.blob(f'{report_id}.html')
    blob.upload_from_string(report_html, content_type='text/html')
    return f'https://storage.googleapis.com/alphatest-reports/{report_id}.html'
```

### Option B: Store HTML in Firestore
```python
def save_report(report_html, report_id):
    db.collection('reports').document(report_id).set({
        'html': report_html,
        'created_at': firestore.SERVER_TIMESTAMP
    })
```

---

## Firestore Data Structure

```
alphatest-482117 (Firestore Database)
│
├── users (collection)
│   ├── user@example.com (document)
│   │   ├── id: "abc123"
│   │   ├── email: "user@example.com"
│   │   ├── name: "John Doe"
│   │   ├── password_hash: "..."
│   │   ├── salt: "..."
│   │   ├── created_at: "2025-01-15T..."
│   │   ├── projects: ["project1", "project2"]
│   │   └── api_keys: [...]
│   │
│   └── another@example.com (document)
│       └── ...
│
├── projects (collection)
│   ├── project_abc123 (document)
│   │   ├── id: "project_abc123"
│   │   ├── name: "My Website"
│   │   ├── url: "https://example.com"
│   │   ├── owner_id: "abc123"
│   │   ├── test_specs: [...]
│   │   └── created_at: "2025-01-15T..."
│   │
│   └── project_def456 (document)
│       └── ...
│
└── reports (collection)
    ├── report_xyz789 (document)
    │   ├── project_id: "project_abc123"
    │   ├── html: "<html>...</html>"
    │   ├── created_at: timestamp
    │   └── status: "completed"
    │
    └── ...
```

---

## Security Rules

Set Firestore security rules to protect user data:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only read/write their own data
    match /users/{email} {
      allow read, write: if request.auth != null && request.auth.token.email == email;
    }

    // Users can only access their own projects
    match /projects/{projectId} {
      allow read, write: if request.auth != null &&
        get(/databases/$(database)/documents/projects/$(projectId)).data.owner_id == request.auth.uid;
    }

    // Reports are readable by project owners
    match /reports/{reportId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
  }
}
```

Apply rules:
```bash
# Save rules to firestore.rules
gcloud firestore databases update --database=default --security-rules=firestore.rules
```

---

## Cost Breakdown

**Free Tier (plenty for small usage):**
- 1 GB storage
- 50,000 document reads/day
- 20,000 document writes/day
- 20,000 document deletes/day

**Typical Usage:**
- 100 users = ~$0.50/month
- 1,000 users = ~$5/month
- 10,000 users = ~$50/month

**Cloud Storage (for reports):**
- $0.020 per GB/month
- $0.004 per 10,000 reads
- Typical: $1-3/month

---

## Testing the Migration

1. **Test locally first:**
```bash
# Install Firestore emulator
gcloud components install cloud-firestore-emulator

# Run emulator
gcloud beta emulators firestore start

# Set environment variable
export FIRESTORE_EMULATOR_HOST=localhost:8080

# Run your app
python server.py
```

2. **Test in production:**
```bash
# Deploy with Firestore enabled
gcloud run deploy alphatest \
  --source . \
  --region=us-central1 \
  --set-env-vars=USE_FIRESTORE=true
```

3. **Verify data persistence:**
   - Create a test user
   - Redeploy the service
   - Login again - user should still exist! ✅

---

## Rollback Plan

If something goes wrong, you can temporarily switch back to JSON:

```python
# In auth.py and server.py
USE_FIRESTORE = os.getenv('USE_FIRESTORE', 'false').lower() == 'true'

if USE_FIRESTORE:
    # Use Firestore
    db = firestore.Client()
else:
    # Use JSON files
    USERS_FILE = Path(__file__).parent / "data" / "users.json"
```

Then deploy without the env var:
```bash
gcloud run deploy alphatest --source . --region=us-central1
```

---

## Next Steps

1. ✅ Enable Firestore (Step 1)
2. ✅ Update requirements.txt (Step 2)
3. ⚠️ **I'll update the code files** (auth.py, server.py)
4. ⚠️ Deploy the updated code
5. ⚠️ Test user signup/login
6. ⚠️ Verify data persists across redeployments

Would you like me to update the code files now to use Firestore?
