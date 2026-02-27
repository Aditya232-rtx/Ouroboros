"""
Quick demo user seed script.
Creates a demo account in Ouroboros postgres for the hackathon demo.
Run with: python scripts/seed_demo_user.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import uuid4
from datetime import datetime

# Ensure DATABASE_URL is set
os.environ.setdefault("DATABASE_URL", "postgresql://ouroboros_user:admin@localhost:5432/ouroboros")
os.environ.setdefault("SECRET_KEY", "demo-hackathon-secret-key-2024")

from src.database.session import SessionLocal, init_db
from src.database.models import User
from src.api.middleware.jwt_utils import get_password_hash

DEMO_EMAIL = "admin@ouroboros.ai"
DEMO_PASSWORD = "Hackathon2024!"
DEMO_NAME = "Ouroboros Admin"

def seed():
    print("Seeding demo user into Ouroboros DB...")
    
    # Create tables if not exist
    try:
        init_db()
        print("[OK] Tables created/verified")
    except Exception as e:
        print(f"[WARN] init_db: {e}")
    
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            print(f"[OK] Demo user already exists: {DEMO_EMAIL}")
            return
        
        user = User(
            user_id=f"u-{uuid4().hex[:12]}",
            email=DEMO_EMAIL,
            hashed_password=get_password_hash(DEMO_PASSWORD),
            full_name=DEMO_NAME,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        print(f"[OK] Demo user created!")
        print(f"  Email:    {DEMO_EMAIL}")
        print(f"  Password: {DEMO_PASSWORD}")
    except Exception as e:
        print(f"[ERROR] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
