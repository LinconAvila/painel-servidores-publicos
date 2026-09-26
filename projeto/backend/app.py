import os
import sqlite3
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


def normalize_nome_param(nome):
    if nome is None or nome.strip() == "":
        raise ValueError("nome é obrigatório")
    return nome.strip()


def fetch_servidores_by_name(nome):
    search_name = normalize_nome_param(nome)
    driver = get_database_driver()
    placeholder = "?" if driver == "sqlite" else "%s"
    sql = (
        "SELECT nome, cargo, uf, orgao "
        "FROM servidores "
        "WHERE LOWER(nome) = LOWER({}) "
        "ORDER BY nome ASC"
    ).format(placeholder)

    conn = build_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (search_name,))
        rows = cursor.fetchall()
        return [
            {
                "nome": row[0],
                "cargo": row[1],
                "uf": row[2],
                "orgao": row[3],
            }
            for row in rows
        ]
    finally:
        conn.close()


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/api/servidores")
def buscar_servidores():
    nome = request.args.get("nome")
    pagina = request.args.get("pagina", default=1, type=int)
    limit = request.args.get("limit", default=20, type=int)

    if nome is None or nome.strip() == "":
        return {"erro": "parametro_invalido", "mensagem": "nome é obrigatório"}, 400

    if pagina is None or pagina < 1:
        return {"erro": "parametro_invalido", "mensagem": "pagina deve ser maior que zero"}, 400
    if limit is None or limit < 1:
        return {"erro": "parametro_invalido", "mensagem": "limit deve ser maior que zero"}, 400

    try:
        resultados = fetch_servidores_by_name(nome)
    except ValueError as exc:
        return {"erro": "parametro_invalido", "mensagem": str(exc)}, 400
    except (sqlite3.Error, psycopg2.Error):
        return {"erro": "timeout", "mensagem": "A busca excedeu o tempo limite"}, 504

    if not resultados:
        return {"erro": "nao_encontrado", "mensagem": "Nenhum servidor encontrado para os critérios informados"}, 404

    if len(resultados) == 1:
        return resultados[0], 200

    total = len(resultados)
    start = (pagina - 1) * limit
    end = start + limit
    pagina_resultados = resultados[start:end]

    if start >= total:
        return {"erro": "nao_encontrado", "mensagem": "Nenhum servidor encontrado para os critérios informados"}, 404

    return {"total": total, "pagina": pagina, "resultados": pagina_resultados}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
