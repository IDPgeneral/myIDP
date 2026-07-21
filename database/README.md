# Database

Aplique os arquivos SQL em ordem numérica no projeto Supabase exclusivo do IDP.

```bash
psql "$DATABASE_URL" -f database/migrations/001_initial_schema.sql
psql "$DATABASE_URL" -f database/migrations/002_seed_products_and_connections.sql
```

As migrations não contêm secrets nem IDs externos reais. O segundo arquivo cria os três produtos, ambientes production e nove contas de provedor com `credential_ref`.
