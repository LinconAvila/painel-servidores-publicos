# Dicionário de Dados

Documentação dos datasets utilizados na aplicação, provenientes do Portal Brasileiro de Dados Abertos (dados.gov.br):

- **Carreiras/Cargos** — servidores ativos do Poder Executivo Federal
- **Aposentados** — servidores aposentados sob o regime jurídico único do Poder Executivo Federal Civil

---

## 1. Dataset: Carreiras/Cargos (ativos)

**Fonte:** `http://repositorio.dados.gov.br/segrt/Carreira_MES/ANO.csv`
**Arquivo utilizado:** `CARREIRA_072026.txt`
**Volume:** 1.090.897 registros

### 1.1. Campos disponíveis

| Campo (dicionário oficial) | Tipo | Formato | Descrição |
|---|---|---|---|
| Nome | Texto | até 60 posições | Nome do servidor/empregado público |
| CPF | Texto | `***NNNNNN**` | CPF parcialmente mascarado |
| Código da Carreira | Texto | até 3 posições | Código do conjunto de classes da mesma profissão |
| Descrição do Cargo/Emprego | Texto | até 40 posições | Nome do cargo/emprego ocupado |
| UF da UPAG de vinculação | Texto | até 2 posições | Sigla da UF da unidade pagadora |
| Denominação do Órgão de atuação | Texto | até 40 posições | Órgão federal ao qual o servidor está vinculado |
| Mês de referência | Data | 2 posições | Mês do snapshot (ex: `07`) |
| Valor da Remuneração | Double | até 16 posições | Rendimento líquido recebido |

---

## 2. Dataset: Aposentados

**Fonte:** `aposentados-MÊS/ANO` (csv, zip+csv)
**Volume:** 677 registros

### 2.1. Campos disponíveis

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

---

## 3. Mapeamento dos campos exigidos pela API

A aplicação precisa buscar por **nome, cargo, UF e órgão** (`GET /api/servidores?...`). Tabela de mapeamento entre o que a API exige e o campo real de cada dataset:

| Critério de busca | Campo em Carreiras/Cargos (ativos) | Campo em Aposentados |
|---|---|---|
| Nome | `Nome` | `Nome` |
| Cargo | `Descrição do Cargo/Emprego` | `Cargo` |
| UF | `UF da UPAG de vinculação` | **não disponível** |
| Órgão | `Denominação do Órgão de atuação` | `Nome do órgão` |

**Observação importante:** o dataset de **Aposentados não possui campo de UF**. A busca por estado, portanto, só retorna resultados do dataset de ativos. Essa limitação será documentada no schema e no relatório final.

---

## 4. Campos que serão usados no schema

Nem todos os campos do dicionário oficial de Aposentados serão levados ao schema — apenas os que sustentam os critérios de busca exigidos (nome, cargo, UF, órgão) mais os campos de identificação/contexto (CPF, período de referência, valor). Os demais campos (classe, padrão, referência, nível, diploma legal, datas de ingresso etc.) existem no CSV de origem, mas não são usados por nenhum endpoint da API, logo ficam fora do schema inicial.

**Carreiras/Cargos (ativos) → schema:**
`nome`, `cpf`, `codigo_carreira`, `descricao_cargo`, `uf_upag`, `orgao`, `mes_referencia`, `valor_remuneracao`

**Aposentados → schema:**
`nome`, `cpf`, `cargo`, `nome_orgao`, `sigla_orgao`, `valor_rendimento_liquido`

---

## 5. Resumo de volume

| Dataset | Registros | Observação |
|---|---|---|
| Carreiras/Cargos (ativos) | 1.090.897 | Referente a 1 mês (07/2026) |
| Aposentados | 677 | Referente ao mesmo período de referência |
