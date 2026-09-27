## Testes de Performance de Banco de Dados - Semana 2

| Tipo de Busca | Filtro Aplicado | Tempo de Execução (ms) | Status (Referência: < 500ms) |
| :--- | :--- | :--- | :--- |
| **Exata** | `nome = 'NOME DE TESTE'` | 0.061 ms | 🟢 Ok (< 500ms) |
| **Categoria** | `cargo = 'ANALISTA'` | 0.047 ms | 🟢 Ok (< 500ms) |
| **Categoria** | `uf = 'RS'` | 25.772 ms | 🟢 Ok (< 500ms) |
| **Categoria** | `orgao = 'MINISTERIO DA EDUCACAO'` | 0.739 ms | 🟢 Ok (< 500ms) |
| **Combinada** | `cargo = 'ANALISTA' AND uf = 'RS'` | 1.427 ms | 🟢 Ok (< 500ms) |
| **Similaridade** | `nome ILIKE '%SILVA%'` | 146.761 ms | 🟢 Ok (< 500ms) |

*Nota: Todas as consultas testadas com o volume real de dados mantiveram-se abaixo da referência de 500ms, com auxílio de índices B-tree e GIN (pg_trgm).*