## Teste de carga da API: correção de gargalos (#58)

### Condições (idênticas nas duas rodadas)

- Backend da `main` (commit `96b3630`), Gunicorn 2 workers x 4 threads, `statement_timeout` de 5 s.
- Banco PostgreSQL 15 em Docker, com 300 mil linhas sintéticas em `servidores_ativos` (IDs >= 990000000), seguidas de `ANALYZE`.
- `RATE_LIMIT` elevado para `100000 per minute` apenas durante o teste, para medir a API e não o limitador.
- Script de carga em biblioteca padrão: 40 requisições por cenário, 8 simultâneas. Todas as respostas foram 200 (sem 429 nem 504).

### Gargalo identificado

A busca por nome exato (`LOWER(nome) = LOWER(...)`) fazia varredura completa. O plano mostrava `Index Scan` em `idx_servidores_ativos_nome` com `Rows Removed by Filter: 299999` (192 ms por consulta isolada), porque o índice era sobre `nome` e não sobre `LOWER(nome)`.

### Correção

Índices de expressão `idx_servidores_ativos_nome_lower` e `idx_servidores_aposentados_nome_lower` em `db/schema.sql` (autoria do Miguel). Para aplicá-los é preciso recriar o volume do banco (`docker compose down -v`), pois o `schema.sql` só roda em volume vazio.

### Resultados (média / p95, em ms)

| Cenário | Antes | Depois |
|---|---|---|
| nome exato | 372 / 444 | **24 / 31** |
| similaridade (`servidor`) | 1059 / 2047 | 1056 / 1697 |
| uf | 144 / 234 | 139 / 212 |
| orgao | 157 / 252 | 149 / 243 |
| cargo+uf | 260 / 386 | 238 / 350 |

Plano isolado do nome exato: 192 ms (`Rows Removed by Filter: 299999`) antes, 0,118 ms depois (`Index Cond` no novo índice).

### Limitações

- A similaridade com o termo `servidor` continua acima de 500 ms porque esse termo casa com 100% das linhas sintéticas. O Postgres então faz varredura completa e calcula `similarity()` para todas, o que é correto para esse caso. Com volume real, o #78 mediu `ILIKE '%SILVA%'` em 146 ms. Este cenário é um pior caso artificial.
- As variações em uf, orgao e cargo+uf estão dentro do ruído da medição.
- As latências são sob 8 requisições simultâneas, não por requisição isolada.