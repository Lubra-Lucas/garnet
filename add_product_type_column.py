
# add_product_type_column.py
"""
Migration script to add product_type column to Product table
Run this once to update existing database schema
"""
from sqlalchemy import text
from db import engine, get_db_info
import sys

def migrate():
    """Add product_type column to Product table"""
    db_info = get_db_info()
    
    print(f"Conectando ao banco de dados: {db_info['type']}")
    print(f"Localização: {db_info['location']}")
    
    with engine.connect() as conn:
        try:
            # Check if column already exists
            if db_info['type'] == 'PostgreSQL':
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='product' AND column_name='product_type'
                """)
            else:  # SQLite
                check_query = text("PRAGMA table_info(product)")
            
            result = conn.execute(check_query)
            
            if db_info['type'] == 'PostgreSQL':
                exists = result.fetchone() is not None
            else:  # SQLite
                columns = [row[1] for row in result.fetchall()]
                exists = 'product_type' in columns
            
            if exists:
                print("✓ Coluna 'product_type' já existe na tabela Product")
                return True
            
            # Add the column
            print("Adicionando coluna 'product_type' à tabela Product...")
            
            alter_query = text("""
                ALTER TABLE product 
                ADD COLUMN product_type VARCHAR DEFAULT 'Acabado'
            """)
            
            conn.execute(alter_query)
            conn.commit()
            
            print("✓ Coluna 'product_type' adicionada com sucesso!")
            print("✓ Todos os produtos existentes foram marcados como 'Acabado' por padrão")
            return True
            
        except Exception as e:
            print(f"✗ Erro durante a migração: {str(e)}")
            conn.rollback()
            return False

if __name__ == "__main__":
    print("=== Migração: Adicionar coluna product_type ===\n")
    success = migrate()
    
    if success:
        print("\n✓ Migração concluída com sucesso!")
        sys.exit(0)
    else:
        print("\n✗ Migração falhou!")
        sys.exit(1)
