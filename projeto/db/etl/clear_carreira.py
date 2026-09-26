import csv
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ENTRADA = os.path.join(BASE_DIR, "CARREIRA_072026.csv")
ARQUIVO_SAIDA = os.path.join(BASE_DIR, "carreira_limpo.csv")

COLUNAS_ESPERADAS = [
    "nome",
    "cpf",
    "codigo_carreira",
    "descricao_cargo",
    "uf_upag",
    "orgao",
    "mes_referencia",
    "valor_remuneracao",
]


COLUNAS_SAIDA = [
    "nome",
    "cpf",
    "codigo_carreira",
    "descricao_cargo",
    "uf_upag",
    "orgao",
    "data_referencia",
    "valor_remuneracao",
]

REGEX_VALOR_LIMPO = re.compile(r"^-?\d+\.\d{2}$")
REGEX_MES_ANO_ARQUIVO = re.compile(r"(\d{2})(\d{4})")


def extrair_ano_do_nome_arquivo(caminho_arquivo):
    nome_base = os.path.basename(caminho_arquivo)
    match = REGEX_MES_ANO_ARQUIVO.search(nome_base)
    if not match:
        raise ValueError(
            f"Não foi possível extrair mês/ano do nome do arquivo: {nome_base}"
        )
    mes, ano = match.groups()
    return mes, ano


def converter_valor_remuneracao(valor_bruto, numero_linha):
    """Converte valor monetário para o formato numeric do Postgres (ponto decimal)."""
    valor = valor_bruto.strip()

    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")

    if not REGEX_VALOR_LIMPO.match(valor):
        raise ValueError(
            f"Linha {numero_linha}: valor_remuneracao em formato inesperado: "
            f"{valor_bruto!r}"
        )

    return valor


def montar_data_referencia(mes_arquivo, mes_linha, ano, numero_linha):
    """Gera data no formato ISO (YYYY-MM-01) a partir do mês da linha e do ano do arquivo."""
    mes_linha = mes_linha.strip().zfill(2)

    if mes_linha != mes_arquivo:
        # Alerta apenas informativo: mês da linha diverge do mês do nome do arquivo
        print(
            f"Aviso (linha {numero_linha}): mes_referencia={mes_linha} "
            f"difere do mês do arquivo ({mes_arquivo}). Usando mês da linha.",
            file=sys.stderr,
        )

    if not mes_linha.isdigit() or not (1 <= int(mes_linha) <= 12):
        raise ValueError(
            f"Linha {numero_linha}: mes_referencia inválido: {mes_linha!r}"
        )

    return f"{ano}-{mes_linha}-01"


def main():
    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)

    mes_arquivo, ano_arquivo = extrair_ano_do_nome_arquivo(ARQUIVO_ENTRADA)
    print(f"Mês/ano identificados pelo nome do arquivo: {mes_arquivo}/{ano_arquivo}")

    total_linhas = 0
    linhas_com_erro = 0

    with open(ARQUIVO_ENTRADA, "r", encoding="utf-8", newline="") as f_in, open(
        ARQUIVO_SAIDA, "w", encoding="utf-8", newline=""
    ) as f_out:
        leitor = csv.DictReader(f_in)

        if leitor.fieldnames != COLUNAS_ESPERADAS:
            raise ValueError(
                "Cabeçalho do arquivo de entrada não confere com o esperado.\n"
                f"Esperado: {COLUNAS_ESPERADAS}\n"
                f"Encontrado: {leitor.fieldnames}"
            )

        escritor = csv.DictWriter(
            f_out,
            fieldnames=COLUNAS_SAIDA,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        escritor.writeheader()

        for numero_linha, linha in enumerate(leitor, start=2):  # linha 1 = cabeçalho
            total_linhas += 1
            try:
                valor_convertido = converter_valor_remuneracao(
                    linha["valor_remuneracao"], numero_linha
                )
                data_referencia = montar_data_referencia(
                    mes_arquivo, linha["mes_referencia"], ano_arquivo, numero_linha
                )
            except ValueError as erro:
                linhas_com_erro += 1
                print(erro, file=sys.stderr)
                continue

            escritor.writerow(
                {
                    "nome": linha["nome"].strip(),
                    "cpf": linha["cpf"].strip(),
                    "codigo_carreira": linha["codigo_carreira"].strip(),
                    "descricao_cargo": linha["descricao_cargo"].strip(),
                    "uf_upag": linha["uf_upag"].strip(),
                    "orgao": linha["orgao"].strip(),
                    "data_referencia": data_referencia,
                    "valor_remuneracao": valor_convertido,
                }
            )

    print(f"\nProcessamento concluído.")
    print(f"Total de linhas lidas: {total_linhas}")
    print(f"Linhas com erro (descartadas): {linhas_com_erro}")
    print(f"Linhas gravadas: {total_linhas - linhas_com_erro}")
    print(f"Arquivo de saída: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()