
#!/usr/bin/env python3
"""
Script to update PurchaseItem table schema to allow nullable raw_material_id and add notes column
"""
from sqlalchemy import text
from db import engine

def update_schema():
    with engine.connect() as conn:
        try:
            # Make raw_material_id nullable
            conn.execute(text("""
                ALTER TABLE purchaseitem 
                ALTER COLUMN raw_material_id DROP NOT NULL;
            """))
            print("✓ raw_material_id column is now nullable")
            
            # Add notes column if it doesn't exist
            conn.execute(text("""
                ALTER TABLE purchaseitem 
                ADD COLUMN IF NOT EXISTS notes TEXT;
            """))
            print("✓ notes column added")
            
            conn.commit()
            print("\n✅ Schema updated successfully!")
            
        except Exception as e:
            print(f"❌ Error updating schema: {str(e)}")
            conn.rollback()

if __name__ == "__main__":
    update_schema()
