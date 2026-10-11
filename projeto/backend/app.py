import os
import sqlite3
import unicodedata
from urllib.parse import urlparse

import psycopg2
from flask import Flask, request

app = Flask(__name__)


def get_database_url():
    return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "postgresql://painel_user:troque_esta_senha@localhost:5432/servidores_federais"


def get_database_driver():
    return "sqlite" if get_database_url().startswith("sqlite") else "postgresql"


def build_db_connection():
    database_url = get_database_url()
    if database_url.startswith("sqlite"):
        db_path = database_url.replace("sqlite:///", "", 1)
        return sqlite3.connect(db_path)

    parsed = urlparse(database_url)
    return psycopg2.connect(
        host=parsed.hostname or os.getenv("POSTGRES_HOST", "localhost"),
        port=parsed.port or int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=parsed.path.lstrip("/") or os.getenv("POSTGRES_DB", "servidores_federais"),
        user=parsed.username or os.getenv("POSTGRES_USER", "painel_user"),
        password=parsed.password or os.getenv("POSTGRES_PASSWORD", "troque_esta_senha"),
    )


def normalize_text(value):
    if value is None:
        return ""
    nfkd = unicodedata.normalize("NFKD", value)
    sem_acento = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return sem_acento.strip().lower()


def fetch_distinct_values(coluna):
    if coluna not in ("cargo", "uf"):
        raise ValueError("coluna inválida")
    conn = build_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT {coluna} FROM servidores")
        return [row[0] for row in cursor.fetchall() if row[0] is not None]
    finally:
        conn.close()


def resolve_valor_real(valor_usuario, coluna):
    """Encontra o valor original no banco correspondente ao valor
    informado pelo usuário, ignorando caixa e acentuação.
    Retorna o valor original do banco, ou None se não existir."""
    valores_distintos = fetch_distinct_values(coluna)
    alvo_normalizado = normalize_text(valor_usuario)
    for valor_original in valores_distintos:
        if normalize_text(valor_original) == alvo_normalizado:
            return valor_original
    return None


UFS_VALIDAS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def validar_uf_formato(uf):
    return uf.upper() in UFS_VALIDAS


# Condição SQL de cada filtro. Só campos listados aqui entram na query
# (whitelist); o valor do usuário nunca é concatenado, só vai por placeholder.
# Para criar um filtro novo basta adicionar uma linha neste dicionário.
FILTROS_SQL = {
    "nome": "LOWER(nome) = LOWER({p})",
    "cargo": "cargo = {p}",
    "uf": "UPPER(uf) = UPPER({p})",
    "orgao": "LOWER(orgao) LIKE LOWER({p}) ESCAPE '\\'",
}


def escape_like(valor):
    """Escapa %, _ e \\ para o usuário não injetar curingas no LIKE."""
    return valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_where(filtros, placeholder):
    """Monta o WHERE com AND entre todos os filtros recebidos."""
    condicoes = []
    params = []
    for campo, valor in filtros.items():
        condicoes.append(FILTROS_SQL[campo].format(p=placeholder))
        if campo == "orgao":
            params.append(f"%{escape_like(valor)}%")
        else:
            params.append(valor)
    return " AND ".join(condicoes), params


def fetch_servidores(filtros, pagina, limit):
    placeholder = "?" if get_database_driver() == "sqlite" else "%s"
    where, params = build_where(filtros, placeholder)
    offset = (pagina - 1) * limit

    sql_count = f"SELECT COUNT(*) FROM servidores WHERE {where}"
    sql = (
        f"SELECT nome, cargo, uf, orgao "
        f"FROM servidores "
        f"WHERE {where} "
        f"ORDER BY nome ASC "
        f"LIMIT {placeholder} OFFSET {placeholder}"
    )

    conn = build_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_count, tuple(params))
        total = cursor.fetchone()[0]

        cursor.execute(sql, tuple(params) + (limit, offset))
        rows = cursor.fetchall()
        resultados = [
            {"nome": row[0], "cargo": row[1], "uf": row[2], "orgao": row[3]}
            for row in rows
        ]
        return total, resultados
    finally:
        conn.close()


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/api/servidores")
def buscar_servidores():
    pagina = request.args.get("pagina", default=1, type=int)
    limit = request.args.get("limit", default=20, type=int)

    if pagina is None or pagina < 1:
        return {"erro": "parametro_invalido", "mensagem": "pagina deve ser maior que zero"}, 400
    if limit is None or limit < 1:
        return {"erro": "parametro_invalido", "mensagem": "limit deve ser maior que zero"}, 400

    nome = request.args.get("nome", "").strip()
    cargo = request.args.get("cargo", "").strip()
    uf = request.args.get("uf", "").strip().upper()
    orgao = request.args.get("orgao", "").strip()

    if not (nome or cargo or uf or orgao):
        return {"erro": "parametro_invalido", "mensagem": "informe ao menos um parâmetro de busca (nome, cargo, uf ou orgao)"}, 400

    if uf and not validar_uf_formato(uf):
        return {"erro": "parametro_invalido", "mensagem": "UF deve ser uma sigla válida de 2 letras"}, 400

    filtros = {}
    try:
        if cargo:
            cargo_real = resolve_valor_real(cargo, "cargo")
            if cargo_real is None:
                return {"erro": "parametro_invalido", "mensagem": "Cargo não corresponde a nenhum registro cadastrado"}, 400
            filtros["cargo"] = cargo_real
        if nome:
            filtros["nome"] = nome
        if uf:
            filtros["uf"] = uf
        if orgao:
            filtros["orgao"] = orgao

        total, resultados = fetch_servidores(filtros, pagina, limit)
    except (sqlite3.Error, psycopg2.Error):
        return {"erro": "timeout", "mensagem": "A busca excedeu o tempo limite"}, 504

    # Quando há nome na busca, valem as regras de nome: sem resultado (ou
    # página inexistente) é 404 e um único registro volta como objeto.
    if "nome" in filtros:
        if total == 0 or not resultados:
            return {"erro": "nao_encontrado", "mensagem": "Nenhum servidor encontrado para os critérios informados"}, 404
        if total == 1:
            return resultados[0], 200

    return {"total": total, "pagina": pagina, "resultados": resultados}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)