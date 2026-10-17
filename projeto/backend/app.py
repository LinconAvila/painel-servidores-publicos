import math
import os
import re
import sqlite3
import time
import unicodedata
from urllib.parse import urlparse

import psycopg2
from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from psycopg2 import errors as pg_errors
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# Atrás do Nginx, o IP que chega no Flask é sempre o do proxy. O ProxyFix lê o
# X-Forwarded-For que o Nginx acrescenta (o último valor, que o cliente não
# controla) para o rate limit enxergar o IP real de cada usuário.
# TRUSTED_PROXIES = quantos proxies existem na frente do backend (0 desliga).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=int(os.getenv("TRUSTED_PROXIES", "1")))

RATE_LIMIT_PADRAO = "60 per minute"


def get_rate_limit():
    """Limite de requisições por IP na busca (variável RATE_LIMIT)."""
    return os.getenv("RATE_LIMIT") or RATE_LIMIT_PADRAO


# Contadores em memória: cada worker do Gunicorn mantém o seu próprio, então o
# limite efetivo por IP pode chegar a (limite x número de workers).
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=[],
)
STATEMENT_TIMEOUT_MS_PADRAO = 5000


def get_statement_timeout_ms():
    """Timeout das queries no PostgreSQL (variável DB_STATEMENT_TIMEOUT_MS)."""
    try:
        return max(1, int(os.getenv("DB_STATEMENT_TIMEOUT_MS", STATEMENT_TIMEOUT_MS_PADRAO)))
    except ValueError:
        return STATEMENT_TIMEOUT_MS_PADRAO


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
        options=f"-c statement_timeout={get_statement_timeout_ms()}",
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


# ---- Validação dos parâmetros de entrada ----

# Únicos parâmetros que a API aceita. Qualquer outro é erro do cliente (400):
# ignorar em silêncio esconderia um erro de integração.
PARAMETROS_PERMITIDOS = frozenset(
    {"nome", "cargo", "uf", "orgao", "similar", "limit", "pagina"}
)
CAMPOS_TEXTO = ("nome", "cargo", "uf", "orgao", "similar")
TEXTO_TAMANHO_MAXIMO = 255  # tamanho da maior coluna de texto (servidores.nome)
INTEIRO_MAXIMO = 2_147_483_647


def erro_parametro(mensagem):
    return {"erro": "parametro_invalido", "mensagem": mensagem}, 400


def erro_parametros_desconhecidos():
    """Mensagem de erro se a requisição trouxe parâmetros fora da lista."""
    desconhecidos = sorted(set(request.args) - PARAMETROS_PERMITIDOS)
    if not desconhecidos:
        return None
    # ascii() devolve o nome entre aspas e com escapes, sem repassar
    # caracteres de controle para a resposta.
    nomes = ", ".join(ascii(nome[:50]) for nome in desconhecidos[:5])
    aceitos = ", ".join(sorted(PARAMETROS_PERMITIDOS))
    return f"parâmetro(s) não reconhecido(s): {nomes}. Parâmetros aceitos: {aceitos}"


def erro_texto_invalido(campo, valor):
    """Mensagem de erro se o texto for grande demais ou tiver caractere de
    controle (inclui NUL, que o PostgreSQL rejeita); None se estiver ok."""
    if len(valor) > TEXTO_TAMANHO_MAXIMO:
        return f"{campo} deve ter no máximo {TEXTO_TAMANHO_MAXIMO} caracteres"
    if any(unicodedata.category(ch) == "Cc" for ch in valor):
        return f"{campo} contém caracteres de controle, que não são permitidos"
    return None


def ler_inteiro_positivo(campo, padrao):
    """Lê um inteiro positivo da query string e devolve (valor, mensagem_erro).
    Parâmetro ausente ou em branco usa o padrão."""
    bruto = request.args.get(campo, "").strip()
    if not bruto:
        return padrao, None
    if not re.fullmatch(r"[+-]?[0-9]+", bruto):
        return None, f"{campo} deve ser um número inteiro"
    try:
        valor = int(bruto)
    except ValueError:  # número com milhares de dígitos
        valor = INTEIRO_MAXIMO + 1
    if valor < 1:
        return None, f"{campo} deve ser maior que zero"
    if valor > INTEIRO_MAXIMO:
        return None, f"{campo} deve ser menor ou igual a {INTEIRO_MAXIMO}"
    return valor, None


def erro_pagina_inexistente(total, limit):
    if total == 0:
        mensagem = "Nenhum servidor encontrado para os critérios informados"
    else:
        total_paginas = -(-total // limit)
        mensagem = f"Página inexistente: o resultado tem apenas {total_paginas} página(s)"
    return {"erro": "nao_encontrado", "mensagem": mensagem}, 404


TIMEOUT_RESPOSTA = {
    "erro": "timeout",
    "mensagem": "A busca demorou muito para responder. Por favor, especifique melhor os filtros.",
}
ERRO_INTERNO_BANCO = {
    "erro": "erro_interno",
    "mensagem": "Erro interno ao consultar o banco",
}


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

        # Página além do fim: nem precisa buscar (e evita um OFFSET gigante).
        if offset > 0 and offset >= total:
            return total, []

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


@app.errorhandler(429)
def limite_excedido(_erro):
    """429 no formato do contrato, com o tempo de espera até a próxima tentativa."""
    espera = 1
    limite_atingido = getattr(request, "view_rate_limit", None)
    if limite_atingido is not None:
        limite, chave = limite_atingido[0], limite_atingido[1:]
        reset_em, _ = limiter.limiter.get_window_stats(limite, *chave)
        espera = max(1, math.ceil(reset_em - time.time()))

    corpo = {
        "erro": "limite_excedido",
        "mensagem": f"Muitas requisições, tente novamente em {espera} segundos",
        "tentar_novamente_em": espera,
    }
    return corpo, 429, {"Retry-After": str(espera)}


@app.route("/api/servidores")
@limiter.limit(get_rate_limit)
def buscar_servidores():
    mensagem = erro_parametros_desconhecidos()
    if mensagem:
        return erro_parametro(mensagem)

    for campo in CAMPOS_TEXTO:
        mensagem = erro_texto_invalido(campo, request.args.get(campo, ""))
        if mensagem:
            return erro_parametro(mensagem)

    pagina, mensagem = ler_inteiro_positivo("pagina", 1)
    if mensagem:
        return erro_parametro(mensagem)

    similar = request.args.get("similar")
    if similar is None:
        limit, mensagem = ler_inteiro_positivo("limit", 20)
        if mensagem:
            return erro_parametro(mensagem)
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
    except pg_errors.QueryCanceled:
        return TIMEOUT_RESPOSTA, 504
    except (sqlite3.Error, psycopg2.Error):
        app.logger.exception("Erro de banco na busca de servidores")
        return ERRO_INTERNO_BANCO, 500

    if similar is not None:
        # Vem tudo numa resposta só (até o limit): total = quantos foram devolvidos.
        return {"total": len(resultados), "pagina": 1, "resultados": resultados}, 200

    # Página além do total de páginas: 404 (página 1 vazia segue sendo 200).
    if pagina > 1 and (pagina - 1) * limit >= total:
        return erro_pagina_inexistente(total, limit)

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