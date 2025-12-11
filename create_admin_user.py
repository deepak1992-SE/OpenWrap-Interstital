#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to create the first admin user
Usage: python3 create_admin_user.py <username> <password> [email]
"""

import sys
import os
from werkzeug.security import generate_password_hash

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection

def create_user(username, password, email=None):
    """Create a new user"""
    try:
        conn = get_db_connection()
        password_hash = generate_password_hash(password)
        conn.execute(
            'INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
            (username, password_hash, email)
        )
        conn.commit()
        conn.close()
        print(f"User '{username}' created successfully!")
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 create_admin_user.py <username> <password> [email]")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else None
    
    create_user(username, password, email)

