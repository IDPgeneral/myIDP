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

## Acesso direto

- não existe tela de login ou sessão no frontend;
- o backend usa um ator interno sem vínculo com a tabela `users`;
- o ator de acesso direto recebe papel Admin;
- `AUTH_DISABLED=false` desativa esse modo e volta a exigir o fluxo JWT legado do backend;
- como o domínio Render é público, conhecer a URL é suficiente para acessar o portal.

## Permissões

O ator direto pode ler, sincronizar, validar catálogo, testar conexões e executar as ações administrativas existentes. Deploy e restart Render continuam exigindo o body de confirmação explícita.

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
