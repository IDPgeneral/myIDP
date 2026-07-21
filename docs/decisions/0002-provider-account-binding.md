# ADR 0002: Vinculação explícita de contas e recursos

Status: aceito

## Contexto

Nomes externos podem colidir entre contas e produtos. Selecionar credencial por nome de serviço ou projeto é inseguro.

## Decisão

Toda chamada externa exige vínculo explícito entre produto, provider account, recurso e ambiente. O banco guarda somente `credential_ref`; o valor é resolvido no processo backend.

## Consequências

- evita mistura de credenciais;
- simplifica auditoria;
- exige cadastro correto do catálogo;
- erros de vínculo retornam conflito antes da chamada externa.
