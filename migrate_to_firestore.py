#!/usr/bin/env python3
"""
Migration script to move data from JSON files to Firestore
Run this ONCE to migrate existing data
"""

import json
from pathlib import Path
from google.cloud import firestore

# Initialize Firestore
db = firestore.Client()

def migrate_users():
    """Migrate users from JSON to Firestore."""
    users_file = Path(__file__).parent / "data" / "users.json"

    if not users_file.exists():
        print("No users.json file found. Skipping user migration.")
        return

    print("Migrating users...")
    users = json.loads(users_file.read_text())

    batch = db.batch()
    for email, user_data in users.items():
        user_ref = db.collection('users').document(email)
        batch.set(user_ref, user_data)

    batch.commit()
    print(f"✓ Migrated {len(users)} users to Firestore")


def migrate_projects():
    """Migrate projects from JSON to Firestore."""
    projects_file = Path(__file__).parent / "data" / "projects.json"

    if not projects_file.exists():
        print("No projects.json file found. Skipping project migration.")
        return

    print("Migrating projects...")
    projects = json.loads(projects_file.read_text())

    batch = db.batch()
    for project_id, project_data in projects.items():
        project_ref = db.collection('projects').document(project_id)
        batch.set(project_ref, project_data)

    batch.commit()
    print(f"✓ Migrated {len(projects)} projects to Firestore")


def verify_migration():
    """Verify data was migrated successfully."""
    print("\nVerifying migration...")

    # Count users
    user_count = len(list(db.collection('users').stream()))
    print(f"✓ Found {user_count} users in Firestore")

    # Count projects
    project_count = len(list(db.collection('projects').stream()))
    print(f"✓ Found {project_count} projects in Firestore")

    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("1. Test the application with Firestore enabled")
    print("2. If everything works, you can delete the JSON files:")
    print("   - data/users.json")
    print("   - data/projects.json")


if __name__ == "__main__":
    print("AlphaTest - Firestore Migration Tool")
    print("=" * 50)
    print()

    try:
        migrate_users()
        migrate_projects()
        verify_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
