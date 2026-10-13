import os
import re
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
        conn = sqlite3.connect(db_path)
        # SQLite (usado nos testes) não tem o similarity() do pg_trgm:
        # registramos uma versão equivalente para a mesma query funcionar.
        conn.create_function("similarity", 2, trigram_similarity)
        return conn

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


# ---- Busca por similaridade ----

SIMILAR_LIMIT_PADRAO = 100
SIMILAR_LIMIT_MAX_PADRAO = 500
SIMILAR_TAMANHO_MINIMO = 2


def get_similar_limit_max():
    """Teto do limit da busca por similaridade (variável SIMILAR_LIMIT_MAX)."""
    try:
        return max(1, int(os.getenv("SIMILAR_LIMIT_MAX", SIMILAR_LIMIT_MAX_PADRAO)))
    except ValueError:
        return SIMILAR_LIMIT_MAX_PADRAO


def _trigramas(texto):
    trigramas = set()
    for palavra in re.findall(r"[^\W_]+", (texto or "").lower()):
        preenchida = f"  {palavra} "
        trigramas.update(preenchida[i:i + 3] for i in range(len(preenchida) - 2))
    return trigramas


def trigram_similarity(a, b):
    """Mesma ideia do similarity() do pg_trgm (0 a 1). Só é usada no SQLite;
    no PostgreSQL quem calcula é a própria extensão."""
    ta, tb = _trigramas(a), _trigramas(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def preparar_similar(texto):
    """Devolve (padrao_like, termo), ou None se o texto for curto demais.

    - padrao_like filtra os registros. Se o usuário usou %, o padrão vale
      como veio (%NOME%SOBRENOME%, NOME SOBRENOME%, NOME%SOBRENOME). Sem %,
      vira "contém". Os caracteres _ e \\ são sempre literais.
    - termo é o texto sem curingas, usado só para ordenar por similaridade.
    """
    texto = texto.strip()
    termo = " ".join(texto.replace("%", " ").split())
    if len(termo.replace(" ", "")) < SIMILAR_TAMANHO_MINIMO:
        return None
    padrao = texto.replace("\\", "\\\\").replace("_", "\\_")
    if "%" not in padrao:
        padrao = f"%{padrao}%"
    return padrao, termo


# Condição SQL de cada filtro. Só campos listados aqui entram na query
# (whitelist); o valor do usuário nunca é concatenado, só vai por placeholder.
# Para criar um filtro novo basta adicionar uma linha neste dicionário.
# {p} = placeholder do driver; {op} = LIKE (SQLite) ou ILIKE (PostgreSQL).
FILTROS_SQL = {
    "nome": "LOWER(nome) = LOWER({p})",
    "cargo": "cargo = {p}",
    "uf": "UPPER(uf) = UPPER({p})",
    "orgao": "LOWER(orgao) LIKE LOWER({p}) ESCAPE '\\'",
    # ILIKE direto na coluna permite ao PostgreSQL usar o índice GIN do pg_trgm.
    "similar": "nome {op} {p} ESCAPE '\\'",
}


def escape_like(valor):
    """Escapa %, _ e \\ para o usuário não injetar curingas no LIKE."""
    return valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_where(filtros, placeholder):
    """Monta o WHERE com AND entre todos os filtros recebidos."""
    operador = "ILIKE" if get_database_driver() == "postgresql" else "LIKE"
    condicoes = []
    params = []
    for campo, valor in filtros.items():
        condicoes.append(FILTROS_SQL[campo].format(p=placeholder, op=operador))
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


def fetch_servidores_similares(filtros, termo, limit):
    """Servidores que casam com os filtros (incluindo o padrão de 'similar'),
    do nome mais parecido com o termo para o menos parecido."""
    placeholder = "?" if get_database_driver() == "sqlite" else "%s"
    where, params = build_where(filtros, placeholder)

    sql = (
        f"SELECT nome, cargo, uf, orgao "
        f"FROM servidores "
        f"WHERE {where} "
        f"ORDER BY similarity(nome, {placeholder}) DESC, nome ASC "
        f"LIMIT {placeholder}"
    )

    conn = build_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params) + (termo, limit))
        return [
            {"nome": row[0], "cargo": row[1], "uf": row[2], "orgao": row[3]}
            for row in cursor.fetchall()
        ]
    finally:
        conn.close()


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/api/servidores")
def buscar_servidores():
    pagina = request.args.get("pagina", default=1, type=int)
    if pagina is None or pagina < 1:
        return {"erro": "parametro_invalido", "mensagem": "pagina deve ser maior que zero"}, 400

    similar = request.args.get("similar")
    if similar is None:
        limit = request.args.get("limit", default=20, type=int)
        if limit is None or limit < 1:
            return {"erro": "parametro_invalido", "mensagem": "limit deve ser maior que zero"}, 400
    else:
        # Na busca por similaridade o limit é o máximo de resultados devolvidos:
        # sem limit vale o padrão e acima do teto é truncado (não é erro).
        limit_bruto = request.args.get("limit", "").strip()
        try:
            limit = int(limit_bruto) if limit_bruto else SIMILAR_LIMIT_PADRAO
        except ValueError:
            limit = 0
        if limit < 1:
            return {"erro": "parametro_invalido", "mensagem": "limit deve ser um inteiro maior que zero"}, 400
        limit = min(limit, get_similar_limit_max())

    nome = request.args.get("nome", "").strip()
    cargo = request.args.get("cargo", "").strip()
    uf = request.args.get("uf", "").strip().upper()
    orgao = request.args.get("orgao", "").strip()

    if similar is None and not (nome or cargo or uf or orgao):
        return {"erro": "parametro_invalido", "mensagem": "informe ao menos um parâmetro de busca (nome, cargo, uf, orgao ou similar)"}, 400

    if uf and not validar_uf_formato(uf):
        return {"erro": "parametro_invalido", "mensagem": "UF deve ser uma sigla válida de 2 letras"}, 400

    termo = None
    filtros = {}
    if similar is not None:
        preparado = preparar_similar(similar)
        if preparado is None:
            return {"erro": "parametro_invalido", "mensagem": "similar deve ter ao menos 2 caracteres, sem contar o %"}, 400
        filtros["similar"], termo = preparado

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

        if similar is not None:
            resultados = fetch_servidores_similares(filtros, termo, limit)
        else:
            total, resultados = fetch_servidores(filtros, pagina, limit)
    except (sqlite3.Error, psycopg2.Error):
        return {"erro": "timeout", "mensagem": "A busca excedeu o tempo limite"}, 504

    if similar is not None:
        # Vem tudo numa resposta só (até o limit): total = quantos foram devolvidos.
        return {"total": len(resultados), "pagina": 1, "resultados": resultados}, 200

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