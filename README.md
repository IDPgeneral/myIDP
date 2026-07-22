# Internal Developer Portal

Portal interno independente para administrar o estado operacional de três produtos:

- MILU Software
- ColorGlass
- Super Excel

O IDP centraliza snapshots de GitHub, Render, Supabase e health checks sem compartilhar credenciais entre produtos e sem expor secrets ao frontend.

## Arquitetura

```text
Browser
  -> Next.js em acesso direto
  -> FastAPI IDP
  -> ProviderAccount do produto
  -> credencial resolvida pela referência
  -> GitHub / Render / Supabase
  -> snapshot sanitizado no PostgreSQL
```

Cada operação de provedor é vinculada a:

```text
product_id
provider_account_id
resource_id
environment
```

O backend nunca escolhe credenciais apenas pelo nome de um recurso.

## Stack

- Frontend: Next.js 16, React 19, TypeScript, App Router
- Backend: FastAPI, Python 3.13, Pydantic, SQLAlchemy
- Banco: Supabase/PostgreSQL
- Agendamento: APScheduler
- Deploy: Render
- CI: GitHub Actions

## Estrutura

```text
developer-portal/
├── frontend/
├── backend/
├── database/migrations/
├── catalog/
├── docs/
├── .github/workflows/
├── render.yaml
└── .env.example
```

## Pré-requisitos

- Python 3.13
- Node.js 22+ (imagem de produção fixada em Node.js 24.14)
- PostgreSQL 15+
- Projeto Supabase exclusivo do IDP
- GitHub App instalado nas três contas GitHub
- Três API keys Render
- Três tokens de Management API do Supabase

## Configuração local

1. Copie as variáveis:

```bash
cp .env.example .env
```

2. Suba o PostgreSQL local opcional:

```bash
docker compose up -d postgres
```

3. Aplique as migrations na ordem:

```bash
psql "$DATABASE_URL" -f database/migrations/001_initial_schema.sql
psql "$DATABASE_URL" -f database/migrations/002_seed_products_and_connections.sql
```

4. Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

5. Frontend:

```bash
cd frontend
npm ci
npm run dev
```

6. Acesse `http://localhost:3000`.

## Acesso

O portal abre diretamente, sem login, e o backend atribui às requisições o papel administrativo interno. Esse modo é controlado por `AUTH_DISABLED=true`; para reativar a autenticação futuramente, altere para `false` e restaure a configuração Supabase Auth no frontend.

O endereço do Render é público. Mesmo sem exibir segredos, qualquer pessoa que conhecer a URL poderá consultar o painel e acionar operações disponíveis.

## Integração das nove contas

A migration cria nove `provider_accounts` somente com referências:

| Produto | GitHub | Render | Supabase |
|---|---|---|---|
| MILU | `GITHUB_INSTALLATION_ID_MILU` | `RENDER_API_KEY_MILU` | `SUPABASE_MANAGEMENT_TOKEN_MILU` |
| ColorGlass | `GITHUB_INSTALLATION_ID_COLORGLASS` | `RENDER_API_KEY_COLORGLASS` | `SUPABASE_MANAGEMENT_TOKEN_COLORGLASS` |
| Super Excel | `GITHUB_INSTALLATION_ID_SUPEREXCEL` | `RENDER_API_KEY_SUPEREXCEL` | `SUPABASE_MANAGEMENT_TOKEN_SUPEREXCEL` |

O IDP também exige `GITHUB_APP_ID` e `GITHUB_APP_PRIVATE_KEY` para gerar tokens temporários por instalação.

## Catálogo YAML

Os arquivos em `catalog/` contêm placeholders `REPLACE_ME`. Substitua somente:

- owner;
- nome completo do repositório;
- Render service ID;
- Supabase project ref;
- health endpoint real.

Nunca inclua tokens, chaves ou connection strings no YAML. Depois valide e importe:

```text
GET  /api/catalog/validate
POST /api/catalog/import
```

A importação exige Admin.

## Sincronização

O frontend lê snapshots locais. As APIs externas não são consultadas ao abrir uma página.

Cada snapshot Render também coleta CPU, memória, tráfego e disco nas últimas 24 horas. Cada snapshot Supabase coleta tamanho do banco, Storage, disco e volume de requisições. A interface sinaliza 75% como aviso e 90% como crítico. Cotas mensais compartilhadas aparecem explicitamente como `workspace` ou `organização`.

Intervalos padrão:

- health checks: 5 minutos;
- Render: 5 minutos;
- GitHub: 10 minutos;
- Supabase: 15 minutos.

Ative com `SYNC_ENABLED=true`. Uma falha em uma conta é registrada e não interrompe os outros produtos.

## ChatGPT MCP para logs de deploy

O backend inclui um MCP opcional e estritamente somente leitura para o ChatGPT consultar deploys e logs de build do Render. Ele publica apenas `list_products`, `list_deploys` e `get_deploy_logs`, permanece desativado por padrão e usa o OAuth 2.1 do Supabase do IDP.

Não configure `OPENAI_API_KEY`: o modelo roda no ChatGPT, enquanto o backend somente entrega dados autorizados. Consulte `docs/mcp-deploy-logs.md` antes de habilitar `MCP_ENABLED`.

## Segurança

- secrets somente nas variáveis do backend;
- referências de credencial no banco;
- CORS restrito;
- acesso direto às rotas `/api` enquanto `AUTH_DISABLED=true`;
- rate limit em memória por instância;
- correlation ID;
- payloads e erros sanitizados;
- health checks com proteção contra hosts privados;
- redirects desabilitados nos health checks;
- nenhuma ação destrutiva;
- deploy e restart exigem Admin e body `{"confirmation":"CONFIRMAR"}`.

Leia `docs/security.md` para detalhes.

## Testes e qualidade

Backend:

```bash
cd backend
ruff check app tests
pyright
pytest -q
python -m compileall -q app tests
```

Frontend:

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Deploy

O `render.yaml` define dois serviços Docker:

- `idp-backend`;
- `idp-frontend`.

O banco permanece no projeto Supabase exclusivo do IDP. Antes do primeiro deploy, aplique as migrations e configure todas as variáveis secretas no serviço backend.

Leia `docs/deployment.md`.

## Limitações atuais

- algumas cotas mensais de Render e Supabase não expõem consumo pela Management API; nesses casos o limite do plano é exibido com o uso marcado como indisponível;
- contagens de issues e PRs usam a primeira página de até 100 itens;
- rate limit é local a cada instância Render;
- scheduler APScheduler pressupõe uma única instância ativa do backend no MVP;
- o modo sem login torna o painel acessível a qualquer pessoa que conheça a URL pública;
- o catálogo inicial contém placeholders e recursos ficam inativos até serem substituídos;
- não há ações destrutivas, SQL arbitrário, editor de secrets ou aplicação automática de migrations.
