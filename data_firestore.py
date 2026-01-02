#!/usr/bin/env python3
"""
AlphaTest - Data Storage Module (Firestore Version)
Handles project storage and retrieval with Cloud Firestore
"""

from google.cloud import firestore
from typing import Dict, Optional
from datetime import datetime

# Initialize Firestore client
db = firestore.Client()


def load_projects() -> Dict:
    """Load all projects from Firestore."""
    projects = {}
    try:
        docs = db.collection('projects').stream()
        for doc in docs:
            project_data = doc.to_dict()
            projects[doc.id] = project_data
    except Exception as e:
        print(f"Error loading projects from Firestore: {e}")
    return projects


def save_projects(projects: Dict):
    """Save projects to Firestore (batch operation)."""
    batch = db.batch()
    for project_id, project_data in projects.items():
        project_ref = db.collection('projects').document(project_id)
        batch.set(project_ref, project_data)
    batch.commit()


def get_project(project_id: str) -> Optional[Dict]:
    """Get a single project by ID."""
    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if project_doc.exists:
        return project_doc.to_dict()
    return None


def create_project(project_id: str, project_data: Dict) -> bool:
    """Create a new project."""
    project_ref = db.collection('projects').document(project_id)

    # Add timestamp
    project_data['created_at'] = firestore.SERVER_TIMESTAMP
    project_data['updated_at'] = firestore.SERVER_TIMESTAMP

    project_ref.set(project_data)
    return True


def update_project(project_id: str, updates: Dict) -> bool:
    """Update an existing project."""
    project_ref = db.collection('projects').document(project_id)

    if not project_ref.get().exists:
        return False

    # Add update timestamp
    updates['updated_at'] = firestore.SERVER_TIMESTAMP

    project_ref.update(updates)
    return True


def delete_project(project_id: str) -> bool:
    """Delete a project."""
    project_ref = db.collection('projects').document(project_id)

    if not project_ref.get().exists:
        return False

    project_ref.delete()
    return True


def get_user_projects(user_id: str) -> Dict:
    """Get all projects for a specific user."""
    projects = {}
    try:
        # Query projects where owner_id matches
        query = db.collection('projects').where('owner_id', '==', user_id)
        docs = query.stream()

        for doc in docs:
            projects[doc.id] = doc.to_dict()
    except Exception as e:
        print(f"Error getting user projects: {e}")

    return projects
