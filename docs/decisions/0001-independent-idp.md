# ADR 0001: IDP como quarto sistema independente

Status: aceito

## Contexto

MILU, ColorGlass e Super Excel possuem contas separadas em GitHub, Render e Supabase. Incorporar o portal em um dos produtos criaria dependência operacional e risco de mistura de credenciais.

## Decisão

Criar frontend, backend, banco, autenticação e deploy exclusivos do IDP.

## Consequências

- falha de um produto não derruba o portal;
- credenciais podem ser rotacionadas independentemente;
- migrations do IDP nunca são aplicadas nos bancos dos produtos;
- o portal precisa de operação e custos próprios.
