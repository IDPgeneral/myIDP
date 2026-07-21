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
- pico de CPU e memória nas últimas 24 horas e os respectivos limites;
- tráfego de saída em 24 horas;
- uso e capacidade de disco persistente quando o serviço possui disco.

No plano Free, a cota de 750 horas mensais é mostrada como cota compartilhada do workspace. A API pública do Render não expõe o consumo mensal dessa cota, portanto o IDP não estima esse número.

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
- tamanho real do banco e dos objetos do Storage por consulta fixa read-only;
- utilização/configuração de disco e contagem de requisições quando a Management API autoriza;
- cotas conhecidas do plano Free, sempre identificando quando são compartilhadas pela organização.

O cliente não consulta API keys do projeto com `reveal`, não altera Auth/RLS e não aceita SQL arbitrário. A única consulta SQL é fixa, somente leitura e usada para medir `pg_database_size` e `storage.objects`.

## Alertas de consumo

- abaixo de 75%: normal;
- de 75% a 89,9%: aviso;
- a partir de 90%: crítico;
- sem valor ou limite exposto pelo provedor: desconhecido, sem estimativas artificiais.

As métricas ficam dentro de `resource_snapshots`, junto ao restante do snapshot sanitizado. Falhas de endpoints opcionais não interrompem a sincronização do recurso.

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
