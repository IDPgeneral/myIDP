# ADR 0003: Leitura por snapshots

Status: aceito

## Contexto

Consultar todas as APIs a cada abertura de página aumenta latência, rate limits e acoplamento a falhas externas.

## Decisão

Sincronizações periódicas/manuais gravam snapshots sanitizados. O frontend consulta somente o banco do IDP.

## Consequências

- dashboard rápido e resiliente;
- data de captura precisa ser exibida;
- dados podem ficar temporariamente desatualizados;
- sincronização requer prevenção de concorrência duplicada.
