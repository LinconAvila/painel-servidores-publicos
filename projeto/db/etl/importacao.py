import psycopg2
import csv

DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = ""
DB_USER = ""
DB_PASS = ""

CSV_APOSENTADOS = "aposentados_limpo.csv"
CSV_ATIVOS = "carreira_limpo.csv"

# Variável de controle: True insere apenas 20 linhas, False insere tudo
AMOSTRA = True 

COLUNS_CSV_ATIVOS = ["nome", "cpf", "codigo_carreira", "descricao_cargo", "uf_upag", "orgao", "valor_remuneracao"]
COLUNS_CSV_APOSENTADOS = ["nome", "cpf", "matricula", "orgao", "sigla_orgao", "cargo", "tipo_aposentaroria", "publicacao_diploma_legal", "tipo_ingresso", "data_ingresso", "remuneracao"]

def insert_data():
    conection = None

    try:
        conection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )

        cursor = conection.cursor()

        # === INSERINDO SERVIDORES ATIVOS ===
        print("Inserindo dados na tabela servidores_ativos...")
        query_ativos = """
            INSERT INTO servidores_ativos 
            (id, nome, cpf, codigo_carreira, cargo, uf, orgao, remuneracao) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        with open(CSV_ATIVOS, mode='r', encoding='utf-8') as f_ativos:
            leitor_ativos = csv.reader(f_ativos)
            cabecalho = next(leitor_ativos) 
            
            indices_ativos = [cabecalho.index(coluna) for coluna in COLUNS_CSV_ATIVOS]
            
            for id_ativo, linha in enumerate(leitor_ativos, start=1):
                if AMOSTRA and id_ativo > 20: 
                    break
                
                valores_extraidos = [linha[i] for i in indices_ativos]
                valores_extraidos[-1] = valores_extraidos[-1].replace(',', '.')
                
                dados_ativos = [id_ativo] + valores_extraidos
                cursor.execute(query_ativos, dados_ativos)


        print("Inserindo dados na tabela servidores_aposentados...")
        query_aposentados = """
            INSERT INTO servidores_aposentados 
            (id, nome, cpf, matricula, orgao, sigla_orgao, cargo, tipo_aposentadoria, data_aposentadoria, tipo_ingresso, data_ingresso, remuneracao) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with open(CSV_APOSENTADOS, mode='r', encoding='utf-8') as f_aposentados:
            leitor_aposentados = csv.reader(f_aposentados)
            cabecalho = next(leitor_aposentados) 
            
            indices_aposentados = [cabecalho.index(coluna) for coluna in COLUNS_CSV_APOSENTADOS]
            
            for id_aposentado, linha in enumerate(leitor_aposentados, start=1):
                if AMOSTRA and id_aposentado > 20: 
                    break
                
                valores_extraidos = [linha[i] for i in indices_aposentados]
                valores_extraidos[-1] = valores_extraidos[-1].replace(',', '.')
                
                dados_aposentados = [id_aposentado] + valores_extraidos
                cursor.execute(query_aposentados, dados_aposentados)

        conection.commit()
        print("Todos os dados foram inseridos com sucesso!")

    except ValueError as e:
        print(f"Erro de cabeçalho: O nome de uma coluna procurada não existe no CSV. Detalhes: {e}")
    except (Exception, psycopg2.Error) as error:
        print("Falha ao inserir dados:", error)
        if conection:
            conection.rollback()

    finally:
        if conection:
            cursor.close()
            conection.close()

if __name__ == "__main__":
    insert_data()