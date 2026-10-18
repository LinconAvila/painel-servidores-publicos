import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import psycopg2
from psycopg2 import errors as pg_errors

import app

app.limiter.enabled = False


class ServidoresSearchEndpointTests(unittest.TestCase):
    def setUp(self):
        fd, db_path = tempfile.mkstemp(prefix="servidores_", suffix=".db")
        os.close(fd)
        self.db_path = db_path
        self.original_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE servidores (nome TEXT, cargo TEXT, uf TEXT, orgao TEXT)"
        )
        conn.executemany(
            "INSERT INTO servidores (nome, cargo, uf, orgao) VALUES (?, ?, ?, ?)",
            [
                ("Miguel Casarin", "Político", "RS", "Ministério Rebolar"),
                ("João da Silva", "Analista", "SP", "Ministério da Fazenda"),
                ("Miguel Casarin", "Servidor", "SP", "Tribunal"),
                ("Miguel Casarin", "Diretor", "PR", "Secretaria"),
                ("Maria Oliveira", "Técnica", "RJ", "INSS"),
                ("Ana Souza", "Analista", "SP", "Receita Federal"),
                ("Carlos Pereira", "Analista", "RS", "Ministério da Fazenda"),
            ],
        )
        conn.commit()
        conn.close()
        self.client = app.app.test_client()

    def tearDown(self):
        if self.original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.original_database_url
        os.remove(self.db_path)

    def test_nome_ausente_ou_vazio_retorna_400(self):
        response = self.client.get("/api/servidores")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

        response = self.client.get("/api/servidores?nome=")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

    def test_nome_nao_encontrado_retorna_404(self):
        response = self.client.get("/api/servidores?nome=NomeInexistente")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["erro"], "nao_encontrado")

    def test_nome_com_1_registro_retorna_objeto_unico(self):
        response = self.client.get("/api/servidores?nome=João%20da%20Silva")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["nome"], "João da Silva")
        self.assertNotIsInstance(payload, list)

    def test_nome_e_case_insensitive_mas_a_correspondencia_e_exata(self):
        response = self.client.get("/api/servidores?nome=jo%C3%A3o%20DA%20SILVA")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["nome"], "João da Silva")

        response = self.client.get("/api/servidores?nome=João")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["erro"], "nao_encontrado")

    def test_nome_com_multiplos_registros_retorna_paginacao(self):
        response = self.client.get("/api/servidores?nome=Miguel+Casarin&pagina=1&limit=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["pagina"], 1)
        self.assertEqual(len(payload["resultados"]), 2)
        self.assertIsInstance(payload["resultados"], list)

    def test_query_uses_parameterized_sql(self):
        # A busca agora executa duas queries (COUNT e SELECT paginado):
        # registramos todas e conferimos que nenhuma recebe o valor no texto.
        captured = []
        real_connect = sqlite3.connect

        class SpyCursor:
            def __init__(self, real_cursor):
                self._real_cursor = real_cursor

            def execute(self, sql, params=None):
                captured.append((sql, params))
                if params is not None:
                    return self._real_cursor.execute(sql, params)
                return self._real_cursor.execute(sql)

            def __getattr__(self, name):
                return getattr(self._real_cursor, name)

        class SpyConnection:
            def __init__(self, real_conn):
                self._real_conn = real_conn

            def cursor(self):
                return SpyCursor(self._real_conn.cursor())

            def __getattr__(self, name):
                return getattr(self._real_conn, name)

        def spy_connect(*args, **kwargs):
            return SpyConnection(real_connect(*args, **kwargs))

        with patch.object(sqlite3, "connect", spy_connect):
            self.client.get(
                "/api/servidores",
                query_string={"nome": "João da Silva", "orgao": "Fazenda"},
            )

        self.assertGreaterEqual(len(captured), 2)
        for sql, params in captured:
            self.assertIn("?", sql)
            self.assertNotIn("João da Silva", sql)
            self.assertNotIn("Fazenda", sql)
            self.assertIn("João da Silva", params)
            self.assertIn("%Fazenda%", params)

    def test_payload_sql_injection_nao_quebra_aplicacao(self):
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE servidores; --",
            "\" OR \"\"=\"",
            "Robert'); DROP TABLE servidores;--",
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.get(
                    "/api/servidores", query_string={"nome": payload}
                )
                self.assertIn(response.status_code, (400, 404))
                self.assertIsInstance(response.get_json(), dict)

                conn = sqlite3.connect(self.db_path)
                try:
                    count = conn.execute("SELECT COUNT(*) FROM servidores").fetchone()[0]
                    self.assertEqual(count, 7)
                finally:
                    conn.close()

    def test_uf_valida_sem_resultado_retorna_200_vazio(self):
        response = self.client.get("/api/servidores?uf=BA")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 0)
        self.assertEqual(payload["resultados"], [])

    def test_uf_formato_invalido_retorna_400(self):
        response = self.client.get("/api/servidores?uf=XX")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

        response = self.client.get("/api/servidores?uf=RSS")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

        response = self.client.get("/api/servidores?uf=1A")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

    def test_uf_e_case_insensitive(self):
        response = self.client.get("/api/servidores?uf=rs")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 2)

    def test_uf_com_multiplos_resultados_retorna_paginacao(self):
        response = self.client.get("/api/servidores?uf=SP&pagina=1&limit=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["pagina"], 1)
        self.assertEqual(len(payload["resultados"]), 2)

        response = self.client.get("/api/servidores?uf=SP&pagina=2&limit=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(len(payload["resultados"]), 1)

    def test_cargo_inexistente_retorna_400(self):
        response = self.client.get("/api/servidores?cargo=Astronauta")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

    def test_cargo_e_case_e_acento_insensitive(self):
        response = self.client.get("/api/servidores?cargo=politico")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["resultados"][0]["nome"], "Miguel Casarin")

        response = self.client.get("/api/servidores?cargo=POLITICO")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 1)

    def test_cargo_com_multiplos_resultados_retorna_paginacao(self):
        response = self.client.get("/api/servidores?cargo=Analista&pagina=1&limit=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["pagina"], 1)
        self.assertEqual(len(payload["resultados"]), 2)

        response = self.client.get("/api/servidores?cargo=Analista&pagina=2&limit=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(len(payload["resultados"]), 1)

    # ---- Órgão (correspondência parcial) ----

    def test_orgao_correspondencia_parcial_e_case_insensitive(self):
        response = self.client.get("/api/servidores?orgao=fazenda")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 2)
        nomes = {r["nome"] for r in payload["resultados"]}
        self.assertEqual(nomes, {"João da Silva", "Carlos Pereira"})

        response = self.client.get("/api/servidores?orgao=Ministério")
        self.assertEqual(response.get_json()["total"], 3)

    def test_orgao_sem_resultado_retorna_200_vazio(self):
        response = self.client.get("/api/servidores?orgao=Inexistente")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 0)
        self.assertEqual(payload["resultados"], [])

    def test_orgao_com_multiplos_resultados_retorna_paginacao(self):
        response = self.client.get("/api/servidores?orgao=Ministério&pagina=2&limit=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 3)
        self.assertEqual(payload["pagina"], 2)
        self.assertEqual(len(payload["resultados"]), 1)

    def test_orgao_nao_trata_curingas_do_usuario_como_curinga(self):
        # Sem escape, "%" casaria com todos os 7 registros.
        for curinga in ("%", "_", "\\"):
            with self.subTest(curinga=curinga):
                response = self.client.get(
                    "/api/servidores", query_string={"orgao": curinga}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["total"], 0)

    def test_orgao_com_payload_sql_injection_nao_quebra_aplicacao(self):
        response = self.client.get(
            "/api/servidores", query_string={"orgao": "'; DROP TABLE servidores; --"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 0)

        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM servidores").fetchone()[0]
            self.assertEqual(count, 7)
        finally:
            conn.close()

    # ---- Combinação de filtros (interseção / AND) ----

    def test_combinacao_de_2_filtros_e_intersecao(self):
        # Analista (3 registros) e SP (3 registros): só 2 estão nos dois.
        response = self.client.get("/api/servidores?cargo=Analista&uf=SP")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 2)
        nomes = {r["nome"] for r in payload["resultados"]}
        self.assertEqual(nomes, {"João da Silva", "Ana Souza"})

    def test_combinacao_de_2_filtros_orgao_e_uf(self):
        response = self.client.get("/api/servidores?orgao=Ministério&uf=RS")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 2)
        nomes = {r["nome"] for r in payload["resultados"]}
        self.assertEqual(nomes, {"Miguel Casarin", "Carlos Pereira"})

    def test_combinacao_de_3_filtros_e_intersecao(self):
        response = self.client.get(
            "/api/servidores?cargo=Analista&uf=SP&orgao=Fazenda"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["resultados"][0]["nome"], "João da Silva")

    def test_combinacao_dos_4_filtros_com_resultado_unico_retorna_objeto(self):
        response = self.client.get(
            "/api/servidores",
            query_string={
                "nome": "João da Silva",
                "cargo": "Analista",
                "uf": "SP",
                "orgao": "Fazenda",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["nome"], "João da Silva")
        self.assertNotIn("resultados", payload)

    def test_combinacao_dos_4_filtros_sem_intersecao_retorna_404(self):
        response = self.client.get(
            "/api/servidores",
            query_string={
                "nome": "Miguel Casarin",
                "cargo": "Analista",
                "uf": "SP",
                "orgao": "Fazenda",
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["erro"], "nao_encontrado")

    def test_nome_combinado_com_uf_restringe_homonimos(self):
        # Sozinho, "Miguel Casarin" tem 3 registros; com uf=SP sobra 1.
        response = self.client.get("/api/servidores?nome=Miguel+Casarin&uf=SP")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["cargo"], "Servidor")

    def test_validacao_de_uf_e_cargo_vale_dentro_da_combinacao(self):
        response = self.client.get("/api/servidores?cargo=Analista&uf=XX")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

        response = self.client.get("/api/servidores?cargo=Astronauta&uf=SP")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["erro"], "parametro_invalido")

    def test_combinacao_com_paginacao(self):
        response = self.client.get(
            "/api/servidores?cargo=Analista&orgao=Fazenda&pagina=2&limit=1"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["pagina"], 2)
        self.assertEqual(len(payload["resultados"]), 1)


class SimilarEndpointTests(unittest.TestCase):
    """Busca por similaridade (?similar=&limit=), com dataset próprio."""

    BASE = (
        ("MARIA DA SILVA", "Analista", "SP", "INSS"),
        ("MARIA SILVA SANTOS", "Analista", "RS", "INSS"),
        ("MARIA APARECIDA DA SILVA", "Tecnica", "SP", "MEC"),
        ("JOSE SILVA", "Analista", "SP", "MEC"),
        ("SILVANA COSTA", "Analista", "RJ", "MEC"),
        ("CARLOS PEREIRA", "Analista", "SP", "INSS"),
        ("ANA SOUZA", "Analista", "SP", "INSS"),
    )

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="servidores_similar_", suffix=".db")
        os.close(fd)
        self.original_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.db_path}"

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE servidores (nome TEXT, cargo TEXT, uf TEXT, orgao TEXT)"
        )
        conn.commit()
        conn.close()
        self.inserir(self.BASE)
        self.client = app.app.test_client()

    def tearDown(self):
        if self.original_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.original_database_url
        os.remove(self.db_path)

    def inserir(self, linhas):
        conn = sqlite3.connect(self.db_path)
        conn.executemany(
            "INSERT INTO servidores (nome, cargo, uf, orgao) VALUES (?, ?, ?, ?)",
            linhas,
        )
        conn.commit()
        conn.close()

    def inserir_servidores_numerados(self, quantidade):
        self.inserir(
            [(f"SERVIDOR {i:03d}", "Analista", "SP", "INSS") for i in range(quantidade)]
        )

    @staticmethod
    def nomes(response):
        return [r["nome"] for r in response.get_json()["resultados"]]

    def buscar(self, **params):
        return self.client.get("/api/servidores", query_string=params)

    def test_similar_vazio_ou_curto_retorna_400(self):
        for valor in ("", "   ", "a", "%a%", "%%", " % "):
            with self.subTest(valor=valor):
                response = self.buscar(similar=valor)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["erro"], "parametro_invalido")

    def test_similar_sem_curinga_busca_por_trecho_do_nome(self):
        response = self.buscar(similar="silva")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(self.nomes(response)),
            {
                "MARIA DA SILVA",
                "MARIA SILVA SANTOS",
                "MARIA APARECIDA DA SILVA",
                "JOSE SILVA",
                "SILVANA COSTA",
            },
        )

    def test_similar_ordena_do_mais_parecido_para_o_menos(self):
        nomes = self.nomes(self.buscar(similar="silva"))
        self.assertEqual(nomes[0], "JOSE SILVA")
        notas = [app.trigram_similarity(n, "silva") for n in nomes]
        self.assertEqual(notas, sorted(notas, reverse=True))

    def test_similar_respeita_curingas_informados_pelo_usuario(self):
        marias = {"MARIA DA SILVA", "MARIA SILVA SANTOS", "MARIA APARECIDA DA SILVA"}
        casos = {
            "MARIA%": marias,
            "%MARIA%SILVA%": marias,
            "MARIA%SILVA": {"MARIA DA SILVA", "MARIA APARECIDA DA SILVA"},
            "MARIA SILVA%": {"MARIA SILVA SANTOS"},
            "%SILVA": {"MARIA DA SILVA", "MARIA APARECIDA DA SILVA", "JOSE SILVA"},
        }
        for padrao, esperado in casos.items():
            with self.subTest(padrao=padrao):
                response = self.buscar(similar=padrao)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(self.nomes(response)), esperado)

    def test_similar_nao_trata_underscore_como_curinga(self):
        # Sem escape, "SILV_" casaria com SILVA.
        response = self.buscar(similar="SILV_")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 0)

    def test_similar_sem_resultado_retorna_200_vazio(self):
        response = self.buscar(similar="zzzz")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 0)
        self.assertEqual(payload["resultados"], [])

    def test_similar_combinado_com_outros_filtros(self):
        response = self.buscar(similar="silva", uf="SP")
        self.assertEqual(
            set(self.nomes(response)),
            {"MARIA DA SILVA", "MARIA APARECIDA DA SILVA", "JOSE SILVA"},
        )

        response = self.buscar(similar="silva", uf="SP", cargo="Analista")
        self.assertEqual(set(self.nomes(response)), {"MARIA DA SILVA", "JOSE SILVA"})

    def test_similar_mantem_validacao_de_uf_e_cargo(self):
        self.assertEqual(self.buscar(similar="silva", uf="XX").status_code, 400)
        self.assertEqual(self.buscar(similar="silva", cargo="Astronauta").status_code, 400)

    def test_similar_total_e_a_quantidade_devolvida(self):
        payload = self.buscar(similar="silva").get_json()
        self.assertEqual(payload["total"], len(payload["resultados"]))
        self.assertEqual(payload["pagina"], 1)

    def test_similar_sem_limit_usa_padrao_100(self):
        self.inserir_servidores_numerados(150)
        payload = self.buscar(similar="servidor").get_json()
        self.assertEqual(len(payload["resultados"]), 100)

    def test_similar_respeita_o_limit_informado(self):
        self.inserir_servidores_numerados(150)
        payload = self.buscar(similar="servidor", limit=10).get_json()
        self.assertEqual(len(payload["resultados"]), 10)

    def test_similar_limit_acima_do_teto_configurado_e_truncado(self):
        self.inserir_servidores_numerados(150)
        with patch.dict(os.environ, {"SIMILAR_LIMIT_MAX": "120"}):
            response = self.buscar(similar="servidor", limit=100000)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["resultados"]), 120)

    def test_similar_teto_padrao_e_500(self):
        self.inserir_servidores_numerados(600)
        with patch.dict(os.environ):
            os.environ.pop("SIMILAR_LIMIT_MAX", None)
            response = self.buscar(similar="servidor", limit=100000)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["resultados"]), 500)

    def test_similar_limit_invalido_retorna_400(self):
        for valor in ("0", "-5", "abc"):
            with self.subTest(limit=valor):
                response = self.buscar(similar="silva", limit=valor)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["erro"], "parametro_invalido")

    def test_similar_com_payload_sql_injection_nao_quebra_aplicacao(self):
        payloads = ["' OR '1'='1", "'; DROP TABLE servidores; --", "\" OR \"\"=\""]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.buscar(similar=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["total"], 0)

                conn = sqlite3.connect(self.db_path)
                try:
                    count = conn.execute("SELECT COUNT(*) FROM servidores").fetchone()[0]
                    self.assertEqual(count, len(self.BASE))
                finally:
                    conn.close()


class TimeoutAndDbErrorTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_get_statement_timeout_ms_default(self):
        with patch.dict(os.environ):
            os.environ.pop("DB_STATEMENT_TIMEOUT_MS", None)
            self.assertEqual(app.get_statement_timeout_ms(), 5000)

    def test_get_statement_timeout_ms_custom(self):
        with patch.dict(os.environ, {"DB_STATEMENT_TIMEOUT_MS": "2500"}):
            self.assertEqual(app.get_statement_timeout_ms(), 2500)

    def test_get_statement_timeout_ms_invalid(self):
        with patch.dict(os.environ, {"DB_STATEMENT_TIMEOUT_MS": "invalid"}):
            self.assertEqual(app.get_statement_timeout_ms(), 5000)

    def test_get_statement_timeout_ms_minimum(self):
        with patch.dict(os.environ, {"DB_STATEMENT_TIMEOUT_MS": "-10"}):
            self.assertEqual(app.get_statement_timeout_ms(), 1)

    def test_build_db_connection_passes_statement_timeout_options(self):
        env = {
            "DATABASE_URL": "postgresql://painel_user:troque_esta_senha@localhost:5432/servidores_federais",
            "DB_STATEMENT_TIMEOUT_MS": "3000",
        }
        with patch.dict(os.environ, env), patch("app.psycopg2.connect") as mock_connect:
            app.build_db_connection()
            mock_connect.assert_called_once()
            _, kwargs = mock_connect.call_args
            self.assertEqual(kwargs.get("options"), "-c statement_timeout=3000")

    def test_busca_retorna_504_em_query_canceled(self):
        with patch("app.fetch_servidores", side_effect=pg_errors.QueryCanceled()):
            response = self.client.get("/api/servidores?uf=SP")
        self.assertEqual(response.status_code, 504)
        payload = response.get_json()
        self.assertEqual(payload["erro"], "timeout")
        self.assertIn("demorou muito", payload["mensagem"])

    def test_busca_similar_retorna_504_em_query_canceled(self):
        with patch("app.fetch_servidores_similares", side_effect=pg_errors.QueryCanceled()):
            response = self.client.get("/api/servidores?similar=silva")
        self.assertEqual(response.status_code, 504)
        payload = response.get_json()
        self.assertEqual(payload["erro"], "timeout")

    def test_busca_resolve_cargo_retorna_504_em_query_canceled(self):
        with patch("app.fetch_distinct_values", side_effect=pg_errors.QueryCanceled()):
            response = self.client.get("/api/servidores?cargo=Analista")
        self.assertEqual(response.status_code, 504)
        payload = response.get_json()
        self.assertEqual(payload["erro"], "timeout")

    def test_busca_retorna_500_em_erro_de_banco_psycopg2(self):
        with patch("app.fetch_servidores", side_effect=psycopg2.OperationalError("Conexão recusada")):
            response = self.client.get("/api/servidores?uf=SP")
        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertEqual(payload["erro"], "erro_interno")
        self.assertEqual(payload["mensagem"], "Erro interno ao consultar o banco")

    def test_busca_retorna_500_em_erro_de_banco_sqlite3(self):
        with patch("app.fetch_servidores", side_effect=sqlite3.OperationalError("disk I/O error")):
            response = self.client.get("/api/servidores?uf=SP")
        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertEqual(payload["erro"], "erro_interno")


class ErrosPadraoJsonTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_rota_inexistente_retorna_json_404(self):
        response = self.client.get("/nao-existe")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["erro"], "nao_encontrado")

    def test_metodo_nao_permitido_retorna_json_405(self):
        response = self.client.post("/api/servidores")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["erro"], "metodo_nao_permitido")


if __name__ == "__main__":
    unittest.main()