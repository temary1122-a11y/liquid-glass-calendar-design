"""
Migration: Change is_closed from INTEGER to BOOLEAN in work_days table
Run: python backend/migrations/fix_is_closed_type.py
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from database.db import DATABASE_URL

def migrate():
    print("[migrate] Starting migration: change is_closed from INTEGER to BOOLEAN")
    
    # Fix postgres:// -> postgresql://
    db_url = DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Check current column type
        result = conn.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'work_days' AND column_name = 'is_closed'
        """))
        row = result.fetchone()
        if row:
            print(f"[migrate] Current type of is_closed: {row[0]}")
        
        # Alter column type to BOOLEAN
        print("[migrate] Altering column type to BOOLEAN...")
        conn.execute(text("""
            ALTER TABLE work_days 
            ALTER COLUMN is_closed TYPE BOOLEAN 
            USING (is_closed::int::boolean)
        """))
        conn.commit()
        
        print("[migrate] ✅ Column is_closed changed to BOOLEAN successfully!")
        
        # Verify
        result = conn.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'work_days' AND column_name = 'is_closed'
        """))
        row = result.fetchone()
        print(f"[migrate] New type: {row[0]}")

if __name__ == "__main__":
    migrate()
