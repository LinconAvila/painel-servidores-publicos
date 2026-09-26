import csv
from datetime import datetime

input_file = 'APOSENTADOS_072026.csv'
output_file = 'aposentados_limpo.csv'
header = ["nome", "cpf", "matricula", "orgao", "sigla_orgao", "codigo_orgao_superior", "cargo", "classe", "padrao", "referencia", "nivel", "tipo_aposentaroria", "fundamentacao_inatividade", "nome_diploma_legal", "publicacao_diploma_legal", "tipo_ingresso", "data_ingresso", "remuneracao"]

def format_date(date_str):
    date_str = date_str.strip()
    if not date_str or len(date_str) != 8:
        return ""
    try:
        return datetime.strptime(date_str, '%d%m%Y').strftime('%Y-%m-%d')
    except ValueError:
        return date_str

def format_money(money_str):
    money_str = money_str.strip()
    if not money_str:
        return ""

    money_str = money_str.replace('.', '').replace(',', '.')
    return money_str

def null_byte_remover(iterator):

    for line in iterator:
        yield line.replace('\x00', '')

try:
    # Lendo com latin1 para suportar a codificação do governo e salvando em utf-8 para o Postgres
    with open(input_file, 'r', encoding='latin1') as infile, \
         open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        
        # Limpa as linhas antes de passar para o csv.reader
        clean_lines = null_byte_remover(infile)
        
        # Assumindo que o arquivo original usa ponto e vírgula
        reader = csv.reader(clean_lines, delimiter=';')
        
        # Arquivo final com vírgula padrão do PostgreSQL
        writer = csv.writer(outfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        
        # Escreve o cabeçalho
        writer.writerow(header)
        
        for row in reader:
            if not row:
                continue
                
            cleaned_row = [field.strip() for field in row]
            
            if len(cleaned_row) < 18:
                cleaned_row.extend([''] * (18 - len(cleaned_row)))
            elif len(cleaned_row) > 18:
                cleaned_row = cleaned_row[:18]
                
            # Formata as colunas de data 
            cleaned_row[14] = format_date(cleaned_row[14])
            cleaned_row[16] = format_date(cleaned_row[16])
            
            # Formata a coluna de remuneração 
            cleaned_row[17] = format_money(cleaned_row[17])
            
            writer.writerow(cleaned_row)

    print(f"Sucesso: Arquivo processado e salvo como {output_file}")

except FileNotFoundError:
    print(f"Erro: O arquivo {input_file} não foi encontrado no diretório atual.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")