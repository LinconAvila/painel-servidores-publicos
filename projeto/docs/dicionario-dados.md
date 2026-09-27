# Dicionário de Dados

Documentação dos datasets utilizados na aplicação, provenientes do Portal Brasileiro de Dados Abertos (dados.gov.br):

- **Carreiras/Cargos** — servidores ativos do Poder Executivo Federal
- **Aposentados** — servidores aposentados sob o regime jurídico único do Poder Executivo Federal Civil

> **Decisão de arquitetura:** o banco é composto por **duas tabelas independentes**, sem chave estrangeira entre elas (`servidores_ativos` e `servidores_aposentados`). Não há JOIN entre as duas — consultas que precisam abranger ambas combinam os resultados via `UNION ALL` (no banco) ou merge no backend.

---

## 1. Dataset: Carreiras/Cargos (ativos)

**Fonte:** `http://repositorio.dados.gov.br/segrt/Carreira_MES/ANO.csv`
**Arquivo utilizado:** `CARREIRA_072026.txt`
**Volume:** 1.090.896 registros (após limpeza — remoção de linhas de total/subtotal do arquivo bruto)

### 1.1. Campos disponíveis no dicionário oficial

| Campo (dicionário oficial) | Tipo | Formato | Descrição |
|---|---|---|---|
| Nome | Texto | até 60 posições | Nome do servidor/empregado público |
| CPF | Texto | `***NNNNNN**` | CPF parcialmente mascarado — **não é identificador único** (confirmado: 14.213 pares nome+CPF duplicados no arquivo) |
| Código da Carreira | Texto | até 3 posições | Código do conjunto de classes da mesma profissão |
| Descrição do Cargo/Emprego | Texto | até 40 posições | Nome do cargo/emprego ocupado |
| UF da UPAG de vinculação | Texto | até 2 posições | Sigla da UF da unidade pagadora |
| Denominação do Órgão de atuação | Texto | até 40 posições | Órgão federal ao qual o servidor está vinculado |
| Mês de referência | Data | 2 posições | Mês do snapshot (ex: `07`) |
| Valor da Remuneração | Double | até 16 posições | Rendimento líquido recebido |

### 1.2. Tabela `servidores_ativos` (schema final)

| Coluna | Tipo (SQL) | Origem (dicionário oficial) |
|---|---|---|
| `id` | BIGINT PK | Chave substituta (surrogate key) — nenhum campo de origem é único, ver seção 4 |
| `nome` | VARCHAR(255) | Nome |
| `cpf` | VARCHAR(11) | CPF |
| `codigo_carreira` | VARCHAR(3) | Código da Carreira |
| `cargo` | VARCHAR(45) | Descrição do Cargo/Emprego |
| `uf` | VARCHAR(2) | UF da UPAG de vinculação |
| `orgao` | VARCHAR(45) | Denominação do Órgão de atuação |
| `remuneracao` | NUMERIC(20,2) | Valor da Remuneração |

> Observação: `mes_referencia` do dicionário oficial **não entrou no schema final** — o banco representa um snapshot único (07/2026), então a coluna foi considerada redundante para o escopo atual.

---

## 2. Dataset: Aposentados

**Fonte:** `aposentados-MÊS/ANO` (csv, zip+csv)
**Volume:** 677 registros

### 2.1. Campos disponíveis no dicionário oficial

| Campo (dicionário oficial) | Tipo | Formato | Descrição |
|---|---|---|---|
| Nome | Texto | — | Nome do aposentado |
| CPF | Texto | `***NNNNNN**` | CPF parcialmente mascarado |
| Matrícula do Servidor | Numérico | `OOOOOMMMMMMM` | Matrícula do servidor |
| Nome do órgão | Texto | — | Nome do órgão ao qual o aposentado está vinculado |
| Sigla do órgão | Texto | — | Sigla do órgão |
| Código do órgão superior | Texto | — | Código do órgão de direção |
| Cargo | Texto | — | Cargo do qual se deu a aposentadoria |
| Classe | Texto | `T` | Patamar do cargo efetivo |
| Padrão | Texto | `TTT` | Subdivisão da estrutura remuneratória |
| Referência | Texto | `TT` | Patamar do cargo à data da aposentadoria |
| Nível | Texto | `TTT` | Posicionamento na estrutura remuneratória |
| Tipo de Aposentadoria | Texto | até 27 posições | Classificação sistêmica do tipo |
| Fundamentação da inatividade | Texto | até 40 posições | Legislação que fundamentou a aposentadoria |
| Nome Diploma Legal | Texto | até 60 posições | Título do documento legal |
| Data publicação do Diploma Legal | Data | `DDMMAAAA` | Data de publicação do diploma legal |
| Ocorrência de ingresso no serviço público | Texto | até 50 posições | Tipo de ingresso no serviço público |
| Data de ocorrência de ingresso | Data | `DDMMAAAA` | Data efetiva de ingresso |
| Valor do Rendimento Líquido | Double | até 16 posições | Valor do provento |

### 2.2. Tabela `servidores_aposentados` (schema final)

| Coluna | Tipo (SQL) | Origem (dicionário oficial) |
|---|---|---|
| `id` | BIGINT PK | Chave substituta (surrogate key) |
| `nome` | VARCHAR(255) | Nome |
| `cpf` | VARCHAR(11) | CPF |
| `matricula` | BIGINT | Matrícula do Servidor |
| `orgao` | VARCHAR(45) | Nome do órgão |
| `sigla_orgao` | VARCHAR(255) | Sigla do órgão |
| `cargo` | VARCHAR(45) | Cargo |
| `tipo_aposentadoria` | VARCHAR(255) | Tipo de Aposentadoria |
| `data_aposentadoria` | DATE | Data publicação do Diploma Legal |
| `tipo_ingresso` | VARCHAR(255) | Ocorrência de ingresso no serviço público |
| `data_ingresso` | DATE | Data de ocorrência de ingresso |
| `remuneracao` | NUMERIC(20,2) | Valor do Rendimento Líquido |

> Campos do dicionário oficial que **ficaram fora do schema**: Código do órgão superior, Classe, Padrão, Referência, Nível, Fundamentação da inatividade, Nome Diploma Legal — não são usados por nenhum endpoint da API.

---

## 3. Mapeamento dos campos exigidos pela API

A aplicação precisa buscar por **nome, cargo, UF e órgão** (`GET /api/servidores?...`):

| Critério de busca | Coluna em `servidores_ativos` | Coluna em `servidores_aposentados` |
|---|---|---|
| Nome | `nome` | `nome` |
| Cargo | `cargo` | `cargo` |
| UF | `uf` | **não disponível** |
| Órgão | `orgao` | `orgao` |

**Limitação conhecida:** `servidores_aposentados` não possui coluna de UF — o dataset de origem não traz essa informação. A busca por estado, portanto, retorna resultados apenas de `servidores_ativos`. Essa limitação deve constar no relatório final (seção 7 do enunciado pede a descrição de limitações encontradas).

---

## 4. Chave primária: por que `id` é substituto (surrogate), não natural

Nenhuma combinação de campos disponíveis nos datasets de origem garante unicidade:

| Combinação testada (em `servidores_ativos`) | Duplicatas restantes |
|---|---|
| `nome + cpf` | 14.213 |
| `nome + cpf + orgao + cargo` | 3.951 |
| `nome + cpf + orgao + cargo + remuneracao` | 135 |
| **Todos os campos da linha** | **135** |

Mesmo usando todos os campos da linha inteira, restam 135 duplicatas exatas no arquivo de origem — confirmando que não existe chave natural. Por isso `id` é `BIGINT` gerado de forma independente (surrogate key), e `cpf` é mantido como campo informativo, **sem constraint `UNIQUE`**.

---

## 5. Índices

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Busca exata
CREATE INDEX idx_servidores_ativos_nome  ON servidores_ativos USING BTREE (nome);
CREATE INDEX idx_servidores_ativos_cargo ON servidores_ativos USING BTREE (cargo);
CREATE INDEX idx_servidores_ativos_uf    ON servidores_ativos USING BTREE (uf);
CREATE INDEX idx_servidores_ativos_orgao ON servidores_ativos USING BTREE (orgao);

CREATE INDEX idx_servidores_aposentados_nome  ON servidores_aposentados USING BTREE (nome);
CREATE INDEX idx_servidores_aposentados_cargo ON servidores_aposentados USING BTREE (cargo);
CREATE INDEX idx_servidores_aposentados_orgao ON servidores_aposentados USING BTREE (orgao);

-- Busca por similaridade de nome (endpoint "similar=")
CREATE INDEX idx_servidores_ativos_nome_trgm      ON servidores_ativos USING GIN (nome gin_trgm_ops);
CREATE INDEX idx_servidores_aposentados_nome_trgm ON servidores_aposentados USING GIN (nome gin_trgm_ops);
```

---

## 6. Resumo de volume

| Tabela | Registros | Observação |
|---|---|---|
| `servidores_ativos` | 1.090.896 | Referente a 1 mês (07/2026), após remoção de linhas de total/subtotal |
| `servidores_aposentados` | 677 | Referente ao mesmo período de referência |