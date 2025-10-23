import os
import sqlite3
import inspect
from sqlmodel import SQLModel, Field
from importlib import import_module

# --- CONFIGURAÇÃO ---
# Caminho do banco da instância e fallback para Replit
if os.name == "nt":
    DB_PATH = r"C:\garnet\data\app.db"
else:
    DB_PATH = "/home/runner/Garnet/data/app.db"

print(f"🔗 Conectando ao banco: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- FUNÇÃO AUXILIAR ---
def get_existing_columns(table_name):
    try:
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cursor.fetchall()]
    except Exception:
        return []

# --- LOCALIZAR MODELOS SQLMODEL ---
def get_sqlmodel_classes():
    classes = []
    base_path = os.path.dirname(__file__)
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py") and "venv" not in root:
                module_path = os.path.relpath(os.path.join(root, file), base_path)
                module_name = module_path.replace(os.sep, ".")[:-3]
                try:
                    mod = import_module(module_name)
                    for name, obj in inspect.getmembers(mod, inspect.isclass):
                        if issubclass(obj, SQLModel) and obj != SQLModel:
                            classes.append(obj)
                except Exception:
                    pass
    return classes

# --- EXECUÇÃO ---
migrated = []

for model_class in get_sqlmodel_classes():
    table_name = model_class.__tablename__
    fields = {k: v for k, v in model_class.__annotations__.items() if k != "id"}
    existing = get_existing_columns(table_name)

    if not existing:
        # cria tabela do zero
        print(f"🆕 Criando tabela {table_name}...")
        SQLModel.metadata.create_all(bind=None)
    else:
        for column_name, column_type in fields.items():
            if column_name not in existing:
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT;")
                    migrated.append(f"{table_name}.{column_name}")
                    print(f"✅ Coluna adicionada: {table_name}.{column_name}")
                except Exception as e:
                    print(f"⚠️ Erro ao adicionar {table_name}.{column_name}: {e}")

conn.commit()
conn.close()

if migrated:
    print("\n✨ Migração concluída com sucesso!")
    print("Colunas criadas:")
    for col in migrated:
        print(f"  - {col}")
else:
    print("✅ Nenhuma migração necessária — banco já atualizado.")
