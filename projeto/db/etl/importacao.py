import csv
import io
import os
import time

import psycopg2
from dotenv import load_dotenv

# Carrega as credenciais do arquivo .env (variáveis já definidas no ambiente têm prioridade)
load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")

CSV_APOSENTADOS = "aposentados_limpo.csv"
CSV_ATIVOS = "carreira_limpo.csv"

# Variável de controle: True insere apenas 20 linhas, False insere tudo
AMOSTRA = False

# Quantas linhas são enviadas ao Postgres por vez (controla uso de memória)
TAMANHO_BLOCO = 50_000

# Colunas lidas do CSV (na ordem em que são gravadas no banco, depois do id)
COLUNS_CSV_ATIVOS = ["nome", "cpf", "codigo_carreira", "descricao_cargo", "uf_upag", "orgao", "valor_remuneracao"]
COLUNS_CSV_APOSENTADOS = ["nome", "cpf", "matricula", "orgao", "sigla_orgao", "cargo", "tipo_aposentaroria", "publicacao_diploma_legal", "tipo_ingresso", "data_ingresso", "remuneracao"]

# Colunas de destino no banco (mesma ordem das listas acima, com o id na frente)
COLUNS_DB_ATIVOS = ["id", "nome", "cpf", "codigo_carreira", "cargo", "uf", "orgao", "remuneracao"]
COLUNS_DB_APOSENTADOS = ["id", "nome", "cpf", "matricula", "orgao", "sigla_orgao", "cargo", "tipo_aposentadoria", "data_aposentadoria", "tipo_ingresso", "data_ingresso", "remuneracao"]

# Marcador de NULL do COPY. Com ele, texto vazio continua sendo texto vazio (e não NULL),
# o mesmo comportamento do INSERT original.
NULL_MARK = "\\N"


def copiar_csv(cursor, caminho_csv, tabela, colunas_csv, colunas_db):
    """Lê o CSV e envia para a tabela com COPY, em blocos. Retorna o total de linhas."""
    sql_copy = (
        f"COPY {tabela} ({', '.join(colunas_db)}) "
        f"FROM STDIN WITH (FORMAT csv, NULL '{NULL_MARK}')"
    )
    total = 0
    nomes_vazios = 0

    with open(caminho_csv, mode="r", encoding="utf-8", newline="") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor)
        indices = [cabecalho.index(coluna) for coluna in colunas_csv]

        buffer = io.StringIO()
        escritor = csv.writer(buffer)
        no_bloco = 0

        for id_linha, linha in enumerate(leitor, start=1):
            if AMOSTRA and id_linha > 20:
                break

            valores = [linha[i] for i in indices]
            valores[-1] = valores[-1].replace(",", ".")  # remuneração: vírgula -> ponto
            if valores[0] == "":
                nomes_vazios += 1

            escritor.writerow([id_linha] + valores)
            no_bloco += 1
            total += 1

            if no_bloco >= TAMANHO_BLOCO:
                buffer.seek(0)
                cursor.copy_expert(sql_copy, buffer)
                buffer.seek(0)
                buffer.truncate(0)
                no_bloco = 0
                print(f"  {total:,} linhas enviadas...")

        if no_bloco:
            buffer.seek(0)
            cursor.copy_expert(sql_copy, buffer)

    if nomes_vazios:
        print(f"  Aviso: {nomes_vazios} linha(s) com nome vazio em {caminho_csv} (foram importadas mesmo assim).")
    return total


def insert_data():
    conection = None
    cursor = None

    try:
        conection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
        )
        cursor = conection.cursor()
        inicio = time.time()

        # Limpa as tabelas antes de iniciar a importação para evitar duplicidade.
        # Tudo roda numa única transação: se algo falhar, o rollback restaura os dados antigos.
        print("Limpando dados antigos...")
        cursor.execute("TRUNCATE TABLE servidores_ativos, servidores_aposentados RESTART IDENTITY CASCADE;")

        print("Inserindo dados na tabela servidores_ativos...")
        n_ativos = copiar_csv(cursor, CSV_ATIVOS, "servidores_ativos", COLUNS_CSV_ATIVOS, COLUNS_DB_ATIVOS)

        print("Inserindo dados na tabela servidores_aposentados...")
        n_aposentados = copiar_csv(cursor, CSV_APOSENTADOS, "servidores_aposentados", COLUNS_CSV_APOSENTADOS, COLUNS_DB_APOSENTADOS)

        conection.commit()

        # Atualiza as estatísticas para o planner usar bem os índices (precisa estar fora da transação)
        conection.autocommit = True
        cursor.execute("ANALYZE servidores_ativos;")
        cursor.execute("ANALYZE servidores_aposentados;")

        print(f"Todos os dados foram inseridos com sucesso em {time.time() - inicio:.1f}s!")
        print(f"  servidores_ativos:      {n_ativos:,} linhas")
        print(f"  servidores_aposentados: {n_aposentados:,} linhas")

    except ValueError as e:
        print(f"Erro de cabeçalho: O nome de uma coluna procurada não existe no CSV. Detalhes: {e}")
        if conection:
            conection.rollback()
    except (Exception, psycopg2.Error) as error:
        print("Falha ao inserir dados:", error)
        if conection:
            conection.rollback()

    finally:
        if cursor:
            cursor.close()
        if conection:
            conection.close()


if __name__ == "__main__":
    insert_data()