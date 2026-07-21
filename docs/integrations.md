# Integrações

## GitHub

### Estratégia

Um GitHub App é instalado nas três contas. Cada `provider_account` referencia um installation ID distinto.

Fluxo:

1. gerar JWT RS256 com `GITHUB_APP_ID` e `GITHUB_APP_PRIVATE_KEY`;
2. trocar o JWT por token temporário da instalação selecionada;
3. consultar somente o repositório cadastrado no `ProductResource`;
4. descartar o token depois da chamada.

Permissões mínimas recomendadas:

- Metadata: read;
- Contents: read;
- Actions: read;
- Pull requests: read;
- Issues: read.

O cliente coleta repositório, branch padrão, último commit, workflows, PRs e issues abertas.

## Render

Cada produto usa uma API key diferente. `credential_ref` aponta para a variável correta.

Leitura:

- serviço;
- branch;
- URL;
- deploys recentes;
- commit e status do último deploy.

Ações opcionais:

- trigger deploy;
- restart service.

Ambas exigem Admin, confirmação textual e auditoria. O portal não altera plano, domínio, env vars ou serviços.

## Supabase

Cada produto usa um Management API token diferente. Não usar anon key ou service role key no lugar desse token.

Leitura:

- projeto por project ref;
- organização;
- região;
- status;
- metadados de banco disponíveis;
- health de serviços suportados;
- link de dashboard.

O cliente não consulta API keys do projeto com `reveal`, não executa SQL e não altera Auth/RLS.

## Teste de conexão

`POST /api/provider-accounts/{id}/test`:

- resolve a credencial pela referência;
- executa uma chamada mínima;
- atualiza `connection_status`;
- grava `last_validated_at`;
- armazena erro sanitizado;
- registra auditoria.

## Erros

Categorias internas:

- `authentication_error`;
- `permission_error`;
- `provider_unavailable`;
- `not_found`;
- `not_configured`;
- `error`.

Essas categorias permitem mostrar “IDP sem acesso à conta Render” separadamente de “serviço Render fora do ar”.

## Rate limits

GitHub, Render e Supabase podem limitar requisições. O MVP reduz chamadas usando snapshots e intervalos diferentes por provedor. Respostas HTTP 429 são convertidas em erro sanitizado de indisponibilidade do provedor.
