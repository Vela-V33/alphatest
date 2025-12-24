#!/usr/bin/env python3
"""
AlphaTest - User Authentication Module
Handles user registration, login, and session management
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

# User data directory
USERS_DIR = Path(__file__).parent / "data" / "users"
USERS_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = Path(__file__).parent / "data" / "users.json"


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password with salt."""
    if salt is None:
        salt = secrets.token_hex(32)

    # Use PBKDF2 for password hashing
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return pwd_hash.hex(), salt


def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
    """Verify a password against a hash."""
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == pwd_hash


def load_users() -> Dict:
    """Load all users from file."""
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except:
            return {}
    return {}


def save_users(users: Dict):
    """Save users to file."""
    USERS_FILE.write_text(json.dumps(users, indent=2))


def create_user(email: str, password: str, name: str = "") -> Dict:
    """Create a new user account."""
    users = load_users()

    # Check if user already exists
    email_lower = email.lower().strip()
    if email_lower in users:
        return {'success': False, 'error': 'User already exists'}

    # Hash password
    pwd_hash, salt = hash_password(password)

    # Create user record
    user_id = secrets.token_urlsafe(16)
    users[email_lower] = {
        'id': user_id,
        'email': email_lower,
        'name': name or email_lower.split('@')[0],
        'password_hash': pwd_hash,
        'salt': salt,
        'created_at': datetime.now().isoformat(),
        'provider': 'email',
        'projects': [],
        'last_login': None
    }

    save_users(users)

    return {'success': True, 'user_id': user_id}


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate a user with email and password."""
    users = load_users()
    email_lower = email.lower().strip()

    user = users.get(email_lower)
    if not user:
        return None

    # Verify password
    if verify_password(password, user['password_hash'], user['salt']):
        # Update last login
        user['last_login'] = datetime.now().isoformat()
        users[email_lower] = user
        save_users(users)

        # Return user data (without sensitive info)
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'projects': user.get('projects', [])
        }

    return None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID."""
    users = load_users()
    for email, user in users.items():
        if user['id'] == user_id:
            return {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'projects': user.get('projects', [])
            }
    return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email."""
    users = load_users()
    email_lower = email.lower().strip()
    user = users.get(email_lower)

    if user:
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'projects': user.get('projects', [])
        }
    return None


def create_google_user(email: str, name: str, google_id: str) -> Dict:
    """Create or update a Google OAuth user."""
    users = load_users()
    email_lower = email.lower().strip()

    if email_lower in users:
        # Update existing user
        user = users[email_lower]
        user['name'] = name
        user['google_id'] = google_id
        user['last_login'] = datetime.now().isoformat()
    else:
        # Create new user
        user_id = secrets.token_urlsafe(16)
        user = {
            'id': user_id,
            'email': email_lower,
            'name': name,
            'google_id': google_id,
            'created_at': datetime.now().isoformat(),
            'provider': 'google',
            'projects': [],
            'last_login': datetime.now().isoformat()
        }
        users[email_lower] = user

    save_users(users)

    return {
        'success': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'projects': user.get('projects', [])
        }
    }


def add_project_to_user(user_id: str, project_id: str):
    """Add a project to a user's project list."""
    users = load_users()

    for email, user in users.items():
        if user['id'] == user_id:
            if 'projects' not in user:
                user['projects'] = []
            if project_id not in user['projects']:
                user['projects'].append(project_id)
                users[email] = user
                save_users(users)
            break


def remove_project_from_user(user_id: str, project_id: str):
    """Remove a project from a user's project list."""
    users = load_users()

    for email, user in users.items():
        if user['id'] == user_id:
            if 'projects' in user and project_id in user['projects']:
                user['projects'].remove(project_id)
                users[email] = user
                save_users(users)
            break


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)
