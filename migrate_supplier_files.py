
# migrate_supplier_files.py
"""
Migration script to add certification_files column to Supplier table
Run this once to update the database schema
"""
from sqlmodel import Session, text
from db import engine

def migrate():
    """Add certification_files column to supplier table"""
    with Session(engine) as session:
        try:
            # Try to add the column (will fail if already exists, which is fine)
            session.exec(text(
                "ALTER TABLE supplier ADD COLUMN certification_files TEXT"
            ))
            session.commit()
            print("✅ Migration successful: Added certification_files column")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️ Column already exists, skipping migration")
            else:
                print(f"❌ Migration error: {str(e)}")
                raise

if __name__ == "__main__":
    migrate()
