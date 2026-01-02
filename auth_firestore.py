#!/usr/bin/env python3
"""
AlphaTest - User Authentication Module (Firestore Version)
Handles user registration, login, and session management with Cloud Firestore
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from google.cloud import firestore

# Initialize Firestore client
db = firestore.Client()


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
    """Load all users from Firestore."""
    users = {}
    try:
        docs = db.collection('users').stream()
        for doc in docs:
            user_data = doc.to_dict()
            users[doc.id] = user_data
    except Exception as e:
        print(f"Error loading users from Firestore: {e}")
    return users


def save_users(users: Dict):
    """Save users to Firestore (batch operation)."""
    batch = db.batch()
    for email, user_data in users.items():
        user_ref = db.collection('users').document(email)
        batch.set(user_ref, user_data)
    batch.commit()


def create_user(email: str, password: str, name: str = "") -> Dict:
    """Create a new user account in Firestore."""
    # Check if user already exists
    email_lower = email.lower().strip()
    user_ref = db.collection('users').document(email_lower)

    if user_ref.get().exists:
        return {'success': False, 'error': 'User already exists'}

    # Hash password
    pwd_hash, salt = hash_password(password)

    # Create user record
    user_id = secrets.token_urlsafe(16)
    user_data = {
        'id': user_id,
        'email': email_lower,
        'name': name or email_lower.split('@')[0],
        'password_hash': pwd_hash,
        'salt': salt,
        'created_at': firestore.SERVER_TIMESTAMP,
        'provider': 'email',
        'projects': [],
        'last_login': None
    }

    # Save to Firestore
    user_ref.set(user_data)

    return {'success': True, 'user_id': user_id}


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate a user with email and password."""
    email_lower = email.lower().strip()
    user_ref = db.collection('users').document(email_lower)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return None

    user = user_doc.to_dict()

    # Verify password
    if verify_password(password, user['password_hash'], user['salt']):
        # Update last login
        user_ref.update({
            'last_login': firestore.SERVER_TIMESTAMP
        })

        # Return user data (without sensitive info)
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'provider': user.get('provider', 'email'),
            'projects': user.get('projects', [])
        }

    return None


def get_user(email: str) -> Optional[Dict]:
    """Get user by email."""
    email_lower = email.lower().strip()
    user_ref = db.collection('users').document(email_lower)
    user_doc = user_ref.get()

    if user_doc.exists:
        user = user_doc.to_dict()
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'provider': user.get('provider', 'email'),
            'projects': user.get('projects', [])
        }
    return None


def update_user(email: str, updates: Dict) -> bool:
    """Update user data in Firestore."""
    email_lower = email.lower().strip()
    user_ref = db.collection('users').document(email_lower)

    if not user_ref.get().exists:
        return False

    # Don't allow updating sensitive fields
    sensitive_fields = ['password_hash', 'salt', 'id', 'email', 'created_at']
    safe_updates = {k: v for k, v in updates.items() if k not in sensitive_fields}

    user_ref.update(safe_updates)
    return True


def add_project_to_user(email: str, project_id: str) -> bool:
    """Add a project to user's project list."""
    email_lower = email.lower().strip()
    user_ref = db.collection('users').document(email_lower)

    if not user_ref.get().exists:
        return False

    user_ref.update({
        'projects': firestore.ArrayUnion([project_id])
    })
    return True


def remove_project_from_user(email: str, project_id: str) -> bool:
    """Remove a project from user's project list."""
    email_lower = email.lower().strip()
    user_ref = db.collection('users').document(email_lower)

    if not user_ref.get().exists:
        return False

    user_ref.update({
        'projects': firestore.ArrayRemove([project_id])
    })
    return True
