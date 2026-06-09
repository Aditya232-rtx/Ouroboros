#!/usr/bin/env python3
"""
Database initialization script
Creates all tables in PostgreSQL
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import init_db, engine
from src.database.models import Base

def main():
    print("Initializing Ouroboros AI database...")
    print(f"Database URL: {engine.url}")
    
    # Create all tables
    init_db()
    
    # Show created tables
    print("\nCreated tables:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")
    
    print("\n✅ Database initialization complete!")

if __name__ == "__main__":
    main()
