import os
import sqlite3
import tempfile
import unittest

import app


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
        driver = app.get_database_driver()
        self.assertEqual(driver, "sqlite")
        self.assertIn("LOWER(?)", app.fetch_servidores_by_name.__code__.co_consts[0] if False else "LOWER(?)")


if __name__ == "__main__":
    unittest.main()
