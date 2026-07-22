# Deploy

## 1. Supabase do IDP

Crie um projeto exclusivo para o portal.

Configure:

- PostgreSQL;
- acesso ao banco pelo backend.

Aplique:

```bash
psql "$DATABASE_URL" -f database/migrations/001_initial_schema.sql
psql "$DATABASE_URL" -f database/migrations/002_seed_products_and_connections.sql
```

Não aplique essas migrations nos bancos de MILU, ColorGlass ou Super Excel.

## 2. Backend Render

O serviço `idp-backend` usa `backend/Dockerfile`.

Variáveis obrigatórias:

- `APP_ENV=production`;
- `DATABASE_URL`;
- `FRONTEND_URL`;
- `BACKEND_URL`;
- `AUTH_DISABLED=true`;
- `CORS_ORIGINS`;
- GitHub App e três installation IDs;
- três Render API keys;
- três Supabase Management tokens.

Ative `SYNC_ENABLED=true` somente quando houver uma única instância do scheduler no MVP.

Health check do Render: `/healthz`.

### MCP de logs

O deploy inicial deve manter `MCP_ENABLED=false`. Depois de validar o backend e habilitar o OAuth 2.1 Server no Supabase do IDP, configure `MCP_RESOURCE_URL` com a URL HTTPS terminada em `/mcp` e somente então altere `MCP_ENABLED=true`.

O MCP usa as Render API keys já cadastradas; não adicione chave OpenAI.

## 3. Frontend Render

O serviço `idp-frontend` usa `frontend/Dockerfile`.

Variável pública:

- `NEXT_PUBLIC_BACKEND_URL`.

O portal abre diretamente, sem login. Não configure keys Render, tokens Management ou private key GitHub no frontend.

## 4. Catálogo

Antes de importar:

1. substitua todos os placeholders;
2. confira se cada conexão pertence ao produto correto;
3. valide `GET /api/catalog/validate`;
4. importe `POST /api/catalog/import` como Admin;
5. sincronize uma conexão de cada vez;
6. confira snapshots e auditoria.

## 5. CI

O workflow executa:

Backend:

- Ruff;
- Pyright;
- Pytest;
- compileall.

Frontend:

- npm ci;
- ESLint;
- TypeScript;
- Vitest;
- Next build.

Não configure deploy automático antes dos dois jobs concluírem com sucesso.

## 6. Rollback

Frontend/backend são stateless. Reverta o deploy no Render para a imagem anterior. Migrations devem ser aditivas no MVP; não execute rollback destrutivo sem backup.

## 7. Pós-deploy

- confirmar que `/login` redireciona para `/`;
- testar as nove conexões;
- importar catálogo;
- executar sincronização geral;
- verificar os três cards;
- validar falha controlada removendo temporariamente uma credencial em ambiente de teste;
- conferir correlation ID e auditoria.
