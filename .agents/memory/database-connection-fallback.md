---
name: Database connection fallback
description: Development behavior when the managed PostgreSQL connection is unavailable
---

No ambiente de desenvolvimento, uma conexão PostgreSQL gerenciada inválida ou indisponível deve permitir o uso do SQLite local; em produção, a falha deve continuar explícita para não mascarar uma configuração de banco quebrada.

**Why:** O preview pode conter credenciais PostgreSQL antigas, enquanto o banco SQLite local já possui os dados e o schema necessários para validar a aplicação.

**How to apply:** Preserve essa separação ao alterar a configuração do banco: contingência apenas no desenvolvimento, SSL obrigatório para PostgreSQL e nenhuma exposição de credenciais nos logs ou na interface.