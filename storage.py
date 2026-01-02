#!/usr/bin/env python3
"""
AlphaTest - Storage Layer
Automatically uses Firestore or JSON based on environment
"""

import os

# Check if we should use Firestore
USE_FIRESTORE = os.getenv('USE_FIRESTORE', 'false').lower() == 'true'

if USE_FIRESTORE:
    print("[STORAGE] Using Cloud Firestore for data persistence")
    from auth_firestore import (
        create_user,
        authenticate_user,
        get_user,
        update_user,
        add_project_to_user,
        remove_project_from_user,
        load_users,
        save_users
    )
    from data_firestore import (
        load_projects,
        save_projects,
        get_project,
        create_project,
        update_project,
        delete_project,
        get_user_projects
    )
else:
    print("[STORAGE] Using JSON files for data persistence (WARNING: Data will be lost on redeployment!)")
    # Import from original auth.py
    import auth
    create_user = auth.create_user
    authenticate_user = auth.authenticate_user
    get_user = auth.get_user if hasattr(auth, 'get_user') else None
    update_user = auth.update_user if hasattr(auth, 'update_user') else None
    load_users = auth.load_users
    save_users = auth.save_users

    # Use server.py's original functions for projects
    # These will be imported by server.py directly
    from pathlib import Path
    import json

    DATA_DIR = Path(__file__).parent / "data"
    DATA_DIR.mkdir(exist_ok=True)

    def load_projects():
        """Load all saved projects."""
        projects_file = DATA_DIR / "projects.json"
        if projects_file.exists():
            return json.loads(projects_file.read_text())
        return {}

    def save_projects(projects):
        """Save projects to file."""
        projects_file = DATA_DIR / "projects.json"
        projects_file.write_text(json.dumps(projects, indent=2))

    def get_project(project_id):
        projects = load_projects()
        return projects.get(project_id)

    def create_project(project_id, project_data):
        projects = load_projects()
        projects[project_id] = project_data
        save_projects(projects)
        return True

    def update_project(project_id, updates):
        projects = load_projects()
        if project_id in projects:
            projects[project_id].update(updates)
            save_projects(projects)
            return True
        return False

    def delete_project(project_id):
        projects = load_projects()
        if project_id in projects:
            del projects[project_id]
            save_projects(projects)
            return True
        return False

    def get_user_projects(user_id):
        projects = load_projects()
        return {pid: p for pid, p in projects.items() if p.get('owner_id') == user_id}

    # Functions that may not exist in old auth.py
    if not get_user:
        def get_user(email):
            users = load_users()
            user = users.get(email.lower().strip())
            if user:
                return {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'provider': user.get('provider', 'email'),
                    'projects': user.get('projects', [])
                }
            return None

    if not update_user:
        def update_user(email, updates):
            users = load_users()
            email_lower = email.lower().strip()
            if email_lower in users:
                # Don't allow updating sensitive fields
                sensitive = ['password_hash', 'salt', 'id', 'email', 'created_at']
                safe_updates = {k: v for k, v in updates.items() if k not in sensitive}
                users[email_lower].update(safe_updates)
                save_users(users)
                return True
            return False

    def add_project_to_user(email, project_id):
        users = load_users()
        email_lower = email.lower().strip()
        if email_lower in users:
            if 'projects' not in users[email_lower]:
                users[email_lower]['projects'] = []
            if project_id not in users[email_lower]['projects']:
                users[email_lower]['projects'].append(project_id)
            save_users(users)
            return True
        return False

    def remove_project_from_user(email, project_id):
        users = load_users()
        email_lower = email.lower().strip()
        if email_lower in users and 'projects' in users[email_lower]:
            if project_id in users[email_lower]['projects']:
                users[email_lower]['projects'].remove(project_id)
            save_users(users)
            return True
        return False


# Export all functions
__all__ = [
    'USE_FIRESTORE',
    'create_user',
    'authenticate_user',
    'get_user',
    'update_user',
    'add_project_to_user',
    'remove_project_from_user',
    'load_users',
    'save_users',
    'load_projects',
    'save_projects',
    'get_project',
    'create_project',
    'update_project',
    'delete_project',
    'get_user_projects'
]
