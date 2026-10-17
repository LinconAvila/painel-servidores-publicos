import os
import time
import unittest
from unittest.mock import patch

import app

BUSCA = "/api/servidores?uf=SP"


class RateLimitTests(unittest.TestCase):
    """Rate limiting por IP em GET /api/servidores (issue #49)."""

    def setUp(self):
        # Os outros testes rodam com o limiter desligado (muitas requisições
        # do mesmo IP em poucos segundos). Aqui ele é ligado só durante o teste.
        self._limiter_estava_ativo = app.limiter.enabled
        app.limiter.enabled = True
        app.limiter.reset()

        # Sem dependência de banco: a busca sempre responde 200 com lista vazia.
        patcher = patch.object(app, "fetch_servidores", return_value=(0, []))
        patcher.start()
        self.addCleanup(patcher.stop)

        env = patch.dict(os.environ)
        env.start()
        os.environ.pop("RATE_LIMIT", None)
        self.addCleanup(env.stop)

        self.client = app.app.test_client()

    def tearDown(self):
        app.limiter.reset()
        app.limiter.enabled = self._limiter_estava_ativo

    def requisicoes(self, quantidade, **kwargs):
        return [self.client.get(BUSCA, **kwargs).status_code for _ in range(quantidade)]

    def test_limite_padrao_e_60_por_minuto(self):
        self.assertEqual(app.get_rate_limit(), "60 per minute")

    def test_61a_requisicao_do_mesmo_ip_recebe_429(self):
        codigos = self.requisicoes(61)
        self.assertEqual(codigos[:60], [200] * 60)
        self.assertEqual(codigos[60], 429)

    def test_429_segue_o_contrato_e_informa_o_tempo_de_espera(self):
        self.requisicoes(60)
        response = self.client.get(BUSCA)
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response.is_json)

        corpo = response.get_json()
        self.assertEqual(corpo["erro"], "limite_excedido")
        self.assertIn("tente novamente em", corpo["mensagem"])
        self.assertGreaterEqual(corpo["tentar_novamente_em"], 1)
        self.assertLessEqual(corpo["tentar_novamente_em"], 60)
        self.assertEqual(
            response.headers["Retry-After"], str(corpo["tentar_novamente_em"])
        )

    def test_continua_bloqueado_enquanto_a_janela_nao_expira(self):
        self.requisicoes(60)
        self.assertEqual(self.requisicoes(5), [429] * 5)

    def test_volta_a_funcionar_depois_que_a_janela_expira(self):
        os.environ["RATE_LIMIT"] = "3 per second"
        self.assertEqual(self.requisicoes(4), [200, 200, 200, 429])

        time.sleep(1.2)
        self.assertEqual(self.requisicoes(1), [200])

    def test_limite_e_configuravel_pela_variavel_de_ambiente(self):
        os.environ["RATE_LIMIT"] = "5 per minute"
        self.assertEqual(self.requisicoes(6), [200] * 5 + [429])

    def test_cada_ip_tem_o_seu_proprio_limite(self):
        os.environ["RATE_LIMIT"] = "3 per minute"
        ip_a = {"headers": {"X-Forwarded-For": "10.0.0.1"}}
        ip_b = {"headers": {"X-Forwarded-For": "10.0.0.2"}}

        self.assertEqual(self.requisicoes(4, **ip_a), [200, 200, 200, 429])
        # O IP A estourou o limite, mas o IP B não é afetado.
        self.assertEqual(self.requisicoes(3, **ip_b), [200, 200, 200])
        self.assertEqual(self.requisicoes(1, **ip_b), [429])

    def test_ip_forjado_no_inicio_do_x_forwarded_for_nao_burla_o_limite(self):
        # O Nginx acrescenta o IP real no FIM do cabeçalho. Um cliente que
        # inventa valores no início continua sendo contado como o mesmo IP.
        os.environ["RATE_LIMIT"] = "3 per minute"
        codigos = [
            self.client.get(
                BUSCA, headers={"X-Forwarded-For": f"1.1.1.{n}, 203.0.113.7"}
            ).status_code
            for n in range(5)
        ]
        self.assertEqual(codigos, [200, 200, 200, 429, 429])

    def test_health_nao_entra_no_limite(self):
        os.environ["RATE_LIMIT"] = "2 per minute"
        self.requisicoes(3)  # esgota o limite da busca
        codigos = [self.client.get("/health").status_code for _ in range(20)]
        self.assertEqual(codigos, [200] * 20)

    def test_requisicao_invalida_tambem_conta_no_limite(self):
        # O limite vem antes da validação: quem manda lixo em loop é barrado.
        os.environ["RATE_LIMIT"] = "3 per minute"
        codigos = [
            self.client.get("/api/servidores?uf=XX").status_code for _ in range(4)
        ]
        self.assertEqual(codigos, [400, 400, 400, 429])


if __name__ == "__main__":
    unittest.main()