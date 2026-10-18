## Segurança e limitações do backend (#60)

### Medidas de segurança implementadas

| Risco | Medida | Onde / como foi verificado |
|---|---|---|
| SQL injection | Consultas parametrizadas (`%s` no PostgreSQL, `?` no SQLite dos testes). Nenhum valor da requisição é concatenado no SQL. Cada filtro corresponde a um fragmento de SQL fixo no código (`FILTROS_SQL`), combinados com `AND`; `%` e `_` digitados pelo usuário são escapados (`escape_like`) nas buscas parciais. | #46. Testes com payloads de SQL injection em `nome`, `orgao` e `similar`; item 10 do checklist de code review (#59). |
| Strings e parâmetros inválidos | Só os parâmetros conhecidos são aceitos (os demais retornam 400). Texto limitado a 255 caracteres; caracteres de controle e NUL rejeitados; `uf` com formato válido e `cargo` existente; `pagina` e `limit` inteiros positivos. | #47. `test_validacao_parametros.py`. |
| Página inexistente | Página além do total retorna 404 no formato padrão, sem consultar além do necessário. | #47. |
| Consulta lenta | `statement_timeout` de 5 s no PostgreSQL (`DB_STATEMENT_TIMEOUT_MS`); ao estourar, a API responde 504 com JSON padronizado. | #93. |
| Falha do banco | Erro inesperado retorna 500 com mensagem genérica; o detalhe vai só para o log. | #93. |
| Excesso de requisições | Rate limiting por IP (Flask-Limiter): **60 requisições por minuto** em `GET /api/servidores`, configurável por `RATE_LIMIT`. Acima disso, 429 com JSON e header `Retry-After`. O IP real vem do `X-Forwarded-For` do Nginx (`ProxyFix`); `/health` fica fora do limite. | #95. 10 testes em `test_rate_limit.py` e teste manual no Docker: 130 requisições seguidas retornaram 70 × 200 e 60 × 429, e após 61 s voltou a 200. |
| Custo da busca por similaridade | `limit` padrão de 100 e teto de 500 (`SIMILAR_LIMIT_MAX`); termo com no mínimo 2 caracteres. | #85. |
| Erros fora do padrão | 404, 405 e 500 padrão do Flask convertidos para JSON no mesmo formato `{erro, mensagem}`. | #59 (itens 4 e 5). |
| Segredos no repositório | Nenhum `.env` rastreado nem no histórico; só `.env.example` com placeholders. `debug=True` removido (agora via `FLASK_DEBUG`). | #59 (itens 3, 7 e 8). |

A suíte automatizada do backend tem 85 testes e o `ruff` está limpo (#59).

### Capacidade de atendimento

O Gunicorn roda com 2 workers e 4 threads cada (`--timeout 30`), então atende **no máximo 8 requisições ao mesmo tempo**; as demais esperam na fila. O resultado dos testes de carga (#58) está em `teste-carga.md`: com 8 requisições simultâneas e 300 mil linhas sintéticas, todas as respostas foram 200, sem 429 nem 504. O gargalo encontrado (busca por nome exato sem índice sobre `LOWER(nome)`) foi corrigido e caiu de 372 ms para 24 ms em média.

### Limitações identificadas

| # | Limitação | Impacto | Situação |
|---|---|---|---|
| 1 | **Rate limit por worker.** A contagem fica em memória em cada um dos 2 workers. | O limite efetivo por IP fica entre 60 e 120 por minuto, não exatamente 60 (no teste do Docker passaram 70 de 130). | Não corrigido. Para limite exato seria preciso Redis ou 1 worker. |
| 2 | **`X-Forwarded-For` forjável na porta 5000.** O backend confia no cabeçalho que o Nginx acrescenta. | Quem acessa a porta do backend direto pode burlar o limite por IP. | Não corrigido. Em produção só o Nginx deveria ficar exposto. |
| 3 | **Limite por IP, em janela fixa.** | Usuários atrás do mesmo NAT compartilham o limite; pode haver rajada na virada da janela. Não há autenticação. | Aceito. |
| 4 | **Limite padrão de 60/min pode barrar testes exaustivos.** Um avaliador que dispare muitas buscas do mesmo IP recebe 429. | Respostas 429 legítimas durante a avaliação. | `RATE_LIMIT` é configurável; o valor para a entrega precisa ser decidido pela equipe. |
| 5 | **Busca por similaridade** com termo que casa com quase todas as linhas (`servidor`) levou ~1056 ms em média (p95 1697 ms) no cenário sintético. | Acima da referência de 500 ms; com dados reais, `ILIKE '%SILVA%'` mediu 146 ms. Mitigada por `limit`, teto e timeout de 5 s. | Pior caso artificial; não eliminado. |
| 6 | **Concorrência medida só até 8 requisições simultâneas** (40 por cenário). | Não sabemos como a API se comporta com dezenas ou centenas de conexões paralelas, nem se o timeout de 5 s aparece sob essa carga. | Não testado. |
| 7 | **Senha padrão no código.** `get_database_url` tem o fallback `troque_esta_senha` quando a variável não está definida. | Risco se subir sem configurar o ambiente. | Pendente (item 9 do #59). |
| 8 | **Variáveis `RATE_LIMIT` e `TRUSTED_PROXIES`** não estão no `.env.example` nem no compose. | Configuração do limite fica pouco visível. | Pendente. |
| 9 | **Sem HTTPS, autenticação ou cabeçalhos HTTP de segurança** configurados. | API pública de leitura de dados públicos; não tratado. | Fora do escopo. |
| 10 | **Mensagem do 429 no singular** ("1 segundos"). | Cosmético. | Não corrigido. |

### Revisão
Pendente: leitura e revisão por pelo menos um outro integrante antes da consolidação final (critério de pronto do #60).