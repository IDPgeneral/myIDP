# MCP somente leitura para logs de deploy

O backend expõe opcionalmente um servidor MCP Streamable HTTP em `/mcp`. Ele foi limitado a leitura de metadados de deploy e logs de build do Render.

## Ferramentas

- `list_products`: lista os aliases de produtos e serviços cadastrados;
- `list_deploys`: consulta os deploys recentes de um serviço;
- `get_deploy_logs`: consulta logs de build do deploy indicado ou do deploy mais recente; quando houver mais dados, os cursores retornados podem buscar a página seguinte.

Não existem ferramentas MCP para deploy, restart, limpeza de cache, rollback, edição de variáveis ou alteração do banco.

## Segurança

- `MCP_ENABLED=false` é o padrão e impede que as rotas sejam montadas;
- a autenticação usa o OAuth 2.1 Server do projeto Supabase do próprio IDP;
- tokens são validados por assinatura, issuer, audience, expiração, scopes e e-mail administrativo;
- todos os tools declaram `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true` e `openWorldHint=false`;
- produto e serviço são resolvidos pelo catálogo interno; o cliente não fornece API keys nem escolhe Service IDs arbitrários;
- a API Render é consultada com `type=build`, período máximo de seis horas e até 100 entradas;
- payloads são sanitizados antes de retornar ao cliente;
- o texto dos logs é tratado como conteúdo não confiável e nunca como instrução.

## OAuth

O Supabase do IDP atua como authorization server. O endpoint MCP atua como resource server e publica os metadados RFC 9728 em:

```text
/.well-known/oauth-protected-resource/mcp
```

Scopes obrigatórios:

```text
openid email
```

O frontend inclui a tela de consentimento em `/oauth/consent` e a decisão autenticada em `/api/oauth/decision`. A habilitação do OAuth 2.1, a configuração desse Authorization Path e o cadastro do app no ChatGPT são feitos somente depois que o código estiver publicado e os endpoints HTTPS definitivos estiverem disponíveis.

## Variáveis

```text
MCP_ENABLED=false
MCP_RESOURCE_URL=https://SEU-BACKEND.onrender.com/mcp
MCP_MAX_LOG_LINES=100
```

`SUPABASE_URL`, `BACKEND_URL` e `ALLOWED_ADMIN_EMAILS` já são usados pelo backend. Não existe `OPENAI_API_KEY` nessa integração.
