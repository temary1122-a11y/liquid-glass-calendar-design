"""
Manual database backup script for Render Postgres.

Usage:
    python scripts/backup.py

This script creates a backup of the database and saves it to a file.
"""

import os
import subprocess
from datetime import datetime

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:LE315K4b80hrPd0f@db.yhfrygwnvtyutsakouoq.supabase.co:5432/postgres")

def create_backup():
    """Create a backup of the database using pg_dump."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.sql"
    
    print(f"[BACKUP] Creating backup: {backup_filename}")
    
    try:
        # Extract connection details from DATABASE_URL
        if DATABASE_URL.startswith("postgresql://"):
            db_url = DATABASE_URL.replace("postgresql://", "")
        else:
            db_url = DATABASE_URL
        
        # Run pg_dump
        command = f"pg_dump {db_url} > {backup_filename}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = os.path.getsize(backup_filename)
            print(f"[BACKUP] ✅ Backup created successfully: {backup_filename} ({file_size} bytes)")
            return backup_filename
        else:
            print(f"[BACKUP] ❌ Error creating backup: {result.stderr}")
            return None
    except Exception as e:
        print(f"[BACKUP] ❌ Exception: {e}")
        return None

def main():
    """Main function."""
    print("[BACKUP] Starting database backup...")
    backup_file = create_backup()
    
    if backup_file:
        print(f"[BACKUP] Backup saved to: {backup_file}")
    else:
        print("[BACKUP] Backup failed")

if __name__ == "__main__":
    main()
