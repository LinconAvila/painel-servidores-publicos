"""Tratamento de entrada inválida no GET /api/servidores (issue #47).

Cobre os 3 cenários da issue, sempre no formato de erro do contrato
(docs/openapi.yaml): {"erro": "...", "mensagem": "..."}:
  1. string com caractere de controle ou grande demais -> 400
  2. parâmetro de busca desconhecido                    -> 400
  3. página além do total de páginas                    -> 404
"""

import os
import sqlite3
import tempfile
import unittest

import app


class ValidacaoParametrosTests(unittest.TestCase):
    TOTAL = 25  # 25 servidores de SP, "Analista", no INSS

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="servidores_valida_", suffix=".db")
        os.close(fd)
        self.original_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.db_path}"

        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE servidores (nome TEXT, cargo TEXT, uf TEXT, orgao TEXT)")
        conn.executemany(
            "INSERT INTO servidores (nome, cargo, uf, orgao) VALUES (?, ?, ?, ?)",
            [(f"SERVIDOR {i:02d}", "Analista", "SP", "INSS") for i in range(self.TOTAL)],
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

    def buscar(self, **params):
        return self.client.get("/api/servidores", query_string=params)

    def assertErro(self, response, status, erro):
        """Status e formato exatos do contrato: só "erro" e "mensagem"."""
        self.assertEqual(response.status_code, status)
        payload = response.get_json()
        self.assertEqual(set(payload), {"erro", "mensagem"})
        self.assertEqual(payload["erro"], erro)
        self.assertIsInstance(payload["mensagem"], str)
        self.assertTrue(payload["mensagem"])

    # ---- 2. Parâmetro desconhecido ----

    def test_parametro_desconhecido_sozinho_retorna_400(self):
        response = self.buscar(campo_invalido="x")
        self.assertErro(response, 400, "parametro_invalido")
        self.assertIn("campo_invalido", response.get_json()["mensagem"])

    def test_parametro_desconhecido_junto_de_parametros_validos_nao_e_ignorado(self):
        casos = [
            {"uf": "SP", "campo_invalido": "x"},
            {"nome": "SERVIDOR 01", "foo": "1"},
            {"similar": "servidor", "bar": "1"},
            {"cargo": "Analista", "pagina": 1, "limit": 5, "page": 2},
            {"orgao": "INSS", "UF": "SP"},  # nomes de parâmetro são sensíveis a caixa
        ]
        for params in casos:
            with self.subTest(params=params):
                self.assertErro(self.buscar(**params), 400, "parametro_invalido")

    def test_mensagem_lista_os_parametros_aceitos(self):
        mensagem = self.buscar(foo="1").get_json()["mensagem"]
        for aceito in ("nome", "cargo", "uf", "orgao", "similar", "limit", "pagina"):
            self.assertIn(aceito, mensagem)

    def test_nome_de_parametro_desconhecido_nao_vaza_caractere_de_controle(self):
        response = self.buscar(**{"x\x00y\ny": "1"})
        self.assertErro(response, 400, "parametro_invalido")
        mensagem = response.get_json()["mensagem"]
        self.assertNotIn("\x00", mensagem)
        self.assertNotIn("\n", mensagem)

    def test_todos_os_parametros_conhecidos_continuam_aceitos(self):
        self.assertEqual(self.buscar(uf="SP", pagina=1, limit=10).status_code, 200)
        self.assertEqual(
            self.buscar(nome="SERVIDOR 01", cargo="Analista", uf="SP", orgao="INSS").status_code,
            200,
        )
        self.assertEqual(self.buscar(similar="servidor", limit=5).status_code, 200)

    # ---- 1. String inválida ----

    def test_caractere_de_controle_em_qualquer_campo_de_texto_retorna_400(self):
        for campo in ("nome", "cargo", "uf", "orgao", "similar"):
            for caractere in ("\x00", "\x07", "\n", "\t", "\x1b", "\x7f"):
                with self.subTest(campo=campo, caractere=repr(caractere)):
                    valor = f"AB{caractere}CD"
                    response = self.buscar(**{campo: valor})
                    self.assertErro(response, 400, "parametro_invalido")
                    self.assertIn(campo, response.get_json()["mensagem"])

    def test_caractere_de_controle_nao_chega_ao_banco(self):
        # NUL derrubaria o psycopg2 (-> 504 enganoso); aqui tem que ser 400
        # mesmo combinado com filtros válidos.
        response = self.buscar(uf="SP", orgao="INS\x00S")
        self.assertErro(response, 400, "parametro_invalido")

    def test_texto_grande_demais_retorna_400(self):
        limite = app.TEXTO_TAMANHO_MAXIMO
        for campo in ("nome", "cargo", "uf", "orgao", "similar"):
            with self.subTest(campo=campo):
                response = self.buscar(**{campo: "A" * (limite + 1)})
                self.assertErro(response, 400, "parametro_invalido")
                self.assertIn(str(limite), response.get_json()["mensagem"])

    def test_texto_no_tamanho_maximo_e_aceito(self):
        limite = app.TEXTO_TAMANHO_MAXIMO
        response = self.buscar(orgao="A" * limite)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 0)

    def test_acentos_espacos_e_pontuacao_comuns_continuam_validos(self):
        for orgao in ("Ministério da Fazenda", "  INSS  ", "Sec. de Saúde - RS", "D'Ávila"):
            with self.subTest(orgao=orgao):
                self.assertEqual(self.buscar(orgao=orgao).status_code, 200)

    # ---- pagina / limit inválidos (não podem virar default em silêncio) ----

    def test_pagina_e_limit_invalidos_retornam_400(self):
        invalidos = ["abc", "1.5", "0", "-1", "1_0", "1e3", "99999999999999999999", "9" * 5000]
        for campo in ("pagina", "limit"):
            for valor in invalidos:
                with self.subTest(campo=campo, valor=valor[:30]):
                    response = self.buscar(**{"uf": "SP", campo: valor})
                    self.assertErro(response, 400, "parametro_invalido")
                    self.assertIn(campo, response.get_json()["mensagem"])

    def test_pagina_e_limit_em_branco_usam_o_padrao(self):
        response = self.buscar(uf="SP", pagina="", limit="")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["pagina"], 1)
        self.assertEqual(len(payload["resultados"]), 20)  # limit padrão

    # ---- 3. Página além do total ----

    def test_pagina_alem_do_total_retorna_404(self):
        # 25 registros, limit 10 -> 3 páginas.
        response = self.buscar(uf="SP", limit=10, pagina=4)
        self.assertErro(response, 404, "nao_encontrado")
        self.assertIn("3 página", response.get_json()["mensagem"])

    def test_ultima_pagina_existe_e_vem_parcial(self):
        response = self.buscar(uf="SP", limit=10, pagina=3)
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["pagina"], 3)
        self.assertEqual(payload["total"], self.TOTAL)
        self.assertEqual(len(payload["resultados"]), 5)

    def test_pagina_exatamente_no_limite_do_total(self):
        # 25 registros, limit 5 -> 5 páginas cheias; a 6 não existe.
        self.assertEqual(self.buscar(uf="SP", limit=5, pagina=5).status_code, 200)
        self.assertErro(self.buscar(uf="SP", limit=5, pagina=6), 404, "nao_encontrado")

    def test_pagina_alem_do_total_vale_para_todos_os_filtros(self):
        casos = [
            {"uf": "SP"},
            {"cargo": "Analista"},
            {"orgao": "INSS"},
            {"cargo": "Analista", "uf": "SP", "orgao": "INSS"},
        ]
        for filtros in casos:
            with self.subTest(filtros=filtros):
                response = self.buscar(**filtros, limit=10, pagina=99)
                self.assertErro(response, 404, "nao_encontrado")

    def test_pagina_alem_do_total_em_busca_por_nome_retorna_404(self):
        response = self.buscar(nome="SERVIDOR 01", pagina=2)
        self.assertErro(response, 404, "nao_encontrado")

    def test_pagina_gigante_retorna_404_e_nao_estoura_no_banco(self):
        response = self.buscar(uf="SP", pagina=2_147_483_647, limit=2_147_483_647)
        self.assertErro(response, 404, "nao_encontrado")

    def test_pagina_2_sem_nenhum_resultado_retorna_404(self):
        self.assertErro(self.buscar(uf="BA", pagina=2), 404, "nao_encontrado")

    def test_pagina_1_sem_resultado_continua_200_vazio(self):
        # Contrato atual: busca sem resultado (uf/orgao/cargo) é 200 com lista vazia.
        response = self.buscar(uf="BA")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["resultados"], [])

    # ---- Nenhum dos cenários gera 500 / stack trace ----

    def test_nenhuma_entrada_invalida_gera_500(self):
        entradas = [
            {"campo_invalido": "x"},
            {"uf": "SP", "pagina": "abc"},
            {"uf": "SP", "limit": "-1"},
            {"nome": "a\x00b"},
            {"similar": "a\x00b"},
            {"orgao": "x" * 5000},
            {"uf": "SP", "pagina": "9" * 5000},
            {"uf": "SP", "pagina": 10**9},
            {"": "x"},
            {"nome": "ok", "x" * 300: "1"},
        ]
        for params in entradas:
            with self.subTest(params={k[:20]: str(v)[:20] for k, v in params.items()}):
                response = self.buscar(**params)
                self.assertLess(response.status_code, 500)
                self.assertIsInstance(response.get_json(), dict)
                self.assertNotIn("Traceback", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
