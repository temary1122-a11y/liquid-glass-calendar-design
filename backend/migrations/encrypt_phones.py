"""
Migration: encrypt existing plaintext phone numbers in the database.
Run once after setting ENCRYPTION_KEY in environment.

Usage:
  ENCRYPTION_KEY=your_key python migrations/encrypt_phones.py
"""

import os
import sys

# Add parent to path so we can import from backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from database.db import Booking, SessionLocal
from utils.crypto import encrypt_phone


def main():
    if not os.getenv("ENCRYPTION_KEY"):
        print("ERROR: ENCRYPTION_KEY is not set in environment.")
        print("Generate one: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        sys.exit(1)

    with SessionLocal() as db:
        bookings = db.query(Booking).all()
        encrypted_count = 0
        skipped_count = 0

        for b in bookings:
            if not b.phone:
                skipped_count += 1
                continue

            if b.phone.startswith("enc:"):
                skipped_count += 1  # already encrypted
                continue

            b.phone = encrypt_phone(b.phone)
            encrypted_count += 1

        db.commit()
        print(f"Done. Encrypted: {encrypted_count}, Skipped: {skipped_count}")


if __name__ == "__main__":
    main()
