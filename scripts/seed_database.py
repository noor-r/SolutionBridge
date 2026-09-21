import argparse
import os
import sys
from pathlib import Path

# Parse CLI arguments before importing app settings to allow overriding DATABASE_URL
parser = argparse.ArgumentParser(description="Seed SolutionBridge database")
parser.add_argument("--database-url", "-d", help="Override DATABASE_URL (e.g. sqlite:///./solutionbridge_dev.db)")
args, _ = parser.parse_known_args()

if args.database_url:
    os.environ["DATABASE_URL"] = args.database_url

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import SessionLocal, init_db, test_db_connection
from app.db.seed import seed_database
from app.core.logging import logger
from app.core.config import settings


def main():
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    if not test_db_connection():
        print("Initial connection check failed. Attempting schema creation...")
    init_db()
    db = SessionLocal()
    try:
        counts = seed_database(db)
        print("\n--- Database Seeding Completed ---")
        for tbl, count in counts.items():
            print(f"  {tbl.ljust(22)}: {count}")
        print("----------------------------------\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
