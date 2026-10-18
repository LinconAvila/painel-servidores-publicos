## Checklist de code review do backend (#59)

| # | Item | Gravidade | Status | Observação |
|---|---|---|---|---|
| 1 | Sem imports/variáveis não usados | Baixa | OK | `ruff` F401, F841 limpos |
| 2 | Sem código comentado | Baixa | OK | `ruff` ERA001 limpo |
| 3 | `debug=True` removido do `app.run` | Média | OK | Corrigido (60c3cc9); agora via `FLASK_DEBUG` |
| 4 | Erros próprios no formato `{erro, mensagem}` | Alta | OK | 400, 404, 429, 500, 504 |
| 5 | 404/405/500 padrão do Flask em JSON | Média | OK | Handlers + 2 testes; validado com `curl` |
| 6 | `openapi.yaml` consistente com o código | Média | OK | 405 documentado |
| 7 | Nenhum `.env` rastreado hoje | Crítica | OK | Só `.env.example`, com placeholders |
| 8 | Nenhum `.env` ou credencial no histórico | Crítica | OK | `git log --all`: sem `.env`, sem atribuições de segredo |
| 9 | Senha padrão no código | Média | Pendente | Fallback `troque_esta_senha` em `get_database_url`; decidir com o Lincon |
| 10 | Valores de usuário só por placeholder | Crítica | OK | #46 |
| 11 | Testes e lint | Alta | OK | 85 testes, `ruff` limpo |
| 12 | `node_modules` fora do git | Baixa | OK | 0 arquivos rastreados |

Observações (baixa gravidade): `projeto/db/.env.example` usa nomes `DB_*` diferentes de `POSTGRES_*`, confirmar com o Miguel; `RATE_LIMIT` e `TRUSTED_PROXIES` não estão no `.env.example` nem o `RATE_LIMIT` no compose.