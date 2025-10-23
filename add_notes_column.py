
import os
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
    exit(1)

print(f"🔗 Conectando ao banco PostgreSQL...")

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='formulation' AND column_name='notes'
        """))
        
        if result.fetchone():
            print("✅ Coluna 'notes' já existe na tabela 'formulation'")
        else:
            # Add the column
            conn.execute(text("""
                ALTER TABLE formulation 
                ADD COLUMN notes TEXT
            """))
            conn.commit()
            print("✅ Coluna 'notes' adicionada com sucesso à tabela 'formulation'")
            
except Exception as e:
    print(f"❌ Erro ao adicionar coluna: {str(e)}")
    exit(1)

print("✨ Migração concluída!")
