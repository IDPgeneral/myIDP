# Segurança

## Secrets

O banco armazena somente `credential_ref`. O valor real é lido de uma variável de ambiente do backend no momento da chamada.

Exemplo:

```text
provider_accounts.credential_ref = RENDER_API_KEY_MILU
process.env.RENDER_API_KEY_MILU = valor real
```

Nunca armazenar no banco, YAML, logs ou frontend:

- API keys;
- access tokens;
- private keys;
- senhas;
- service role keys;
- connection strings completas;
- headers Authorization.

## Isolamento entre contas

A resolução de credenciais recebe um `ProviderAccount` já validado. O recurso precisa estar vinculado à mesma conta e produto. O código não procura uma credencial por nome de projeto, nome de serviço ou slug externo.

## Autenticação

- login Google via Supabase Auth;
- sessão enviada como Bearer token;
- backend valida assinatura, expiração, audience e subject;
- e-mail precisa existir na allowlist interna;
- rotas administrativas exigem papel Admin.

## Permissões

Viewer:

- leitura;
- documentação;
- sincronização manual;
- health check manual.

Admin:

- tudo do Viewer;
- catálogo;
- conexões;
- usuários autorizados;
- teste de conexão;
- deploy e restart Render com confirmação.

A autorização é sempre executada no backend.

## Sanitização

`sanitize_payload` remove chaves e valores relacionados a:

- token;
- secret;
- password;
- private key;
- API key;
- Authorization;
- cookie;
- connection string.

Erros enviados ao frontend são resumidos e limitados a 500 caracteres.

## Proteção de health checks

- apenas HTTP/HTTPS;
- DNS resolvido antes da chamada;
- IPs privados, loopback, link-local, reservados e multicast são bloqueados;
- redirects não são seguidos;
- timeout por endpoint;
- body da resposta não é persistido.

## Proteções HTTP

- CORS por allowlist;
- rate limit básico por IP e rota;
- correlation ID em request, response, logs e auditoria;
- métodos CORS limitados;
- health endpoint público mínimo em `/healthz`.

## Ações proibidas

O MVP não permite:

- exclusão de recursos;
- edição de secrets;
- alteração de planos;
- SQL arbitrário;
- migrations automáticas em produtos;
- alteração de RLS/Auth externo;
- terminal remoto;
- mudanças em repositórios GitHub.

## Operação segura

1. rotacionar keys por provedor separadamente;
2. atualizar somente a variável correspondente;
3. executar teste de conexão;
4. conferir auditoria e correlation ID;
5. nunca copiar secret para catálogo ou banco.
