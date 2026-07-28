import io
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.test import APIClient

from auditoria.models import LogSeguranca
from campanhas.models import Campanha
from liderancas.models import Lideranca

from .models import ContatoCRM, InteracaoContato, TarefaContato

Usuario = get_user_model()


class ContatoCRMPermissoesTestCase(TestCase):
    def setUp(self):
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha A",
            nome_candidato="Candidato A",
            cargo_disputado="vereador",
            partido="ABC",
            numero_candidato="12345",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-01-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha B",
            nome_candidato="Candidato B",
            cargo_disputado="vereador",
            partido="XYZ",
            numero_candidato="54321",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-01-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario_a = Usuario.objects.create_user(
            email="mobilizador-a@example.com",
            password="senha123",
            nome_completo="Mobilizador A",
            campanha=self.campanha_a,
            nivel_acesso="mobilizador",
        )
        self.usuario_b = Usuario.objects.create_user(
            email="mobilizador-b@example.com",
            password="senha123",
            nome_completo="Mobilizador B",
            campanha=self.campanha_b,
            nivel_acesso="mobilizador",
        )
        self.financeiro_a = Usuario.objects.create_user(
            email="financeiro-a@example.com",
            password="senha123",
            nome_completo="Financeiro A",
            campanha=self.campanha_a,
            nivel_acesso="financeiro",
        )
        self.visualizador_a = Usuario.objects.create_user(
            email="visualizador-a@example.com",
            password="senha123",
            nome_completo="Visualizador A",
            campanha=self.campanha_a,
            nivel_acesso="visualizador",
        )
        self.lideranca_a = Lideranca.objects.create(
            campanha=self.campanha_a,
            nome_completo="Lideranca A",
            telefone="85999990000",
            tipo_lideranca="comunitaria",
            estado="CE",
            cidade="Fortaleza",
        )
        self.contato_a = ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato A",
            telefone="85911110000",
            cidade="Fortaleza",
            status_funil="novo_contato",
            lideranca_relacionada=self.lideranca_a,
            responsavel_cadastro=self.usuario_a,
            consentimento_comunicacao=True,
            canal_autorizado="whatsapp",
        )
        self.contato_b = ContatoCRM.objects.create(
            campanha=self.campanha_b,
            nome_completo="Contato B",
            telefone="85922220000",
            cidade="Caucaia",
            status_funil="novo_contato",
            responsavel_cadastro=self.usuario_b,
            consentimento_comunicacao=True,
            canal_autorizado="email",
        )
        self.interacao_a = InteracaoContato.objects.create(
            campanha=self.campanha_a,
            contato=self.contato_a,
            tipo="ligacao",
            data_hora=timezone.now(),
            descricao="Primeiro contato telefonico",
            responsavel=self.usuario_a,
        )
        self.tarefa_a = TarefaContato.objects.create(
            campanha=self.campanha_a,
            contato=self.contato_a,
            titulo="Retornar na sexta",
            prazo=timezone.now() + timedelta(days=2),
            concluida=False,
            responsavel=self.usuario_a,
        )
        self.interacao_b = InteracaoContato.objects.create(
            campanha=self.campanha_b,
            contato=self.contato_b,
            tipo="mensagem",
            data_hora=timezone.now(),
            descricao="Contato da outra campanha",
            responsavel=self.usuario_b,
        )
        self.tarefa_b = TarefaContato.objects.create(
            campanha=self.campanha_b,
            contato=self.contato_b,
            titulo="Retorno B",
            prazo=timezone.now() + timedelta(days=1),
            concluida=False,
            responsavel=self.usuario_b,
        )

    def _arquivo_csv(self, conteudo: str, nome: str = "contatos.csv"):
        return SimpleUploadedFile(nome, conteudo.encode("utf-8"), content_type="text/csv")

    def _arquivo_xlsx(self, linhas, nome: str = "contatos.xlsx"):
        workbook = Workbook()
        worksheet = workbook.active
        for linha in linhas:
            worksheet.append(linha)
        buffer = io.BytesIO()
        workbook.save(buffer)
        return SimpleUploadedFile(
            nome,
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_lista_web_mostra_apenas_contatos_da_mesma_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("eleitores:home"))
        self.assertContains(resposta, "Contato A")
        self.assertNotContains(resposta, "Contato B")

    def test_detalhe_web_bloqueia_idor_para_outra_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("eleitores:detalhe", args=[self.contato_b.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_detalhe_web_exibe_interacoes_e_tarefas_do_contato(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("eleitores:detalhe", args=[self.contato_a.pk]))
        self.assertContains(resposta, "Primeiro contato telefonico")
        self.assertContains(resposta, "Retornar na sexta")
        self.assertNotContains(resposta, "Contato da outra campanha")

    def test_kanban_web_respeita_isolamento_por_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("eleitores:kanban"))
        self.assertContains(resposta, "Contato A")
        self.assertNotContains(resposta, "Contato B")

    def test_perfil_financeiro_nao_acessa_crm_web(self):
        self.client.force_login(self.financeiro_a)
        resposta = self.client.get(reverse("eleitores:home"))
        self.assertEqual(resposta.status_code, 403)

    def test_visualizador_nao_pode_criar_contato_na_web(self):
        self.client.force_login(self.visualizador_a)
        resposta = self.client.get(reverse("eleitores:novo"))
        self.assertEqual(resposta.status_code, 403)

    def test_visualizador_nao_pode_importar_ou_exportar(self):
        self.client.force_login(self.visualizador_a)
        resposta_importacao = self.client.get(reverse("eleitores:importar"))
        resposta_exportacao = self.client.get(reverse("eleitores:exportar"), {"formato": "csv"})
        self.assertEqual(resposta_importacao.status_code, 403)
        self.assertEqual(resposta_exportacao.status_code, 403)

    def test_criacao_web_de_interacao_e_tarefa_respeita_contato_da_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta_interacao = self.client.post(
            reverse("eleitores:interacao_nova", args=[self.contato_a.pk]),
            {
                "tipo": "visita",
                "data_hora": "2026-07-29T09:30",
                "descricao": "Visita registrada pelo CRM",
                "responsavel": str(self.usuario_a.pk),
            },
        )
        resposta_tarefa = self.client.post(
            reverse("eleitores:tarefa_nova", args=[self.contato_a.pk]),
            {
                "titulo": "Enviar material",
                "prazo": "2026-07-30T10:00",
                "concluida": "",
                "responsavel": str(self.usuario_a.pk),
            },
        )
        self.assertEqual(resposta_interacao.status_code, 302)
        self.assertEqual(resposta_tarefa.status_code, 302)
        self.assertTrue(InteracaoContato.objects.filter(contato=self.contato_a, descricao__icontains="CRM").exists())
        self.assertTrue(TarefaContato.objects.filter(contato=self.contato_a, titulo="Enviar material").exists())

    def test_criacao_web_de_relacionamento_bloqueia_contato_de_outra_campanha(self):
        self.client.force_login(self.usuario_a)
        resposta_interacao = self.client.get(reverse("eleitores:interacao_nova", args=[self.contato_b.pk]))
        resposta_tarefa = self.client.get(reverse("eleitores:tarefa_nova", args=[self.contato_b.pk]))
        self.assertEqual(resposta_interacao.status_code, 404)
        self.assertEqual(resposta_tarefa.status_code, 404)

    def test_importacao_csv_cria_contato_e_registra_log(self):
        arquivo = self._arquivo_csv(
            "nome_completo;telefone;email;cidade;status_funil;consentimento_comunicacao;canal_autorizado\n"
            "Contato Importado;85933334444;importado@example.com;Fortaleza;interessado;sim;whatsapp\n"
        )
        self.client.force_login(self.usuario_a)
        resposta = self.client.post(
            reverse("eleitores:importar"),
            {
                "arquivo": arquivo,
                "atualizar_existentes": "",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(
            ContatoCRM.objects.filter(
                campanha=self.campanha_a,
                telefone="85933334444",
                consentimento_comunicacao=True,
            ).exists()
        )
        self.assertTrue(LogSeguranca.objects.filter(evento="crm_importacao_contatos", usuario=self.usuario_a).exists())

    def test_importacao_xlsx_atualiza_contato_existente(self):
        arquivo = self._arquivo_xlsx(
            [
                ["nome_completo", "telefone", "cidade", "status_funil", "tags"],
                ["Contato A Atualizado", "85911110000", "Fortaleza", "apoiador", "bairro-centro"],
            ]
        )
        self.client.force_login(self.usuario_a)
        resposta = self.client.post(
            reverse("eleitores:importar"),
            {
                "arquivo": arquivo,
                "atualizar_existentes": "on",
            },
        )
        self.assertEqual(resposta.status_code, 200)
        self.contato_a.refresh_from_db()
        self.assertEqual(self.contato_a.nome_completo, "Contato A Atualizado")
        self.assertEqual(self.contato_a.status_funil, ContatoCRM.EtapasFunil.APOIADOR)
        self.assertIn("bairro-centro", self.contato_a.tags)

    def test_exportacao_csv_retorna_apenas_contatos_autorizados_da_campanha(self):
        ContatoCRM.objects.create(
            campanha=self.campanha_a,
            nome_completo="Contato Sem Consentimento",
            telefone="85944445555",
            cidade="Fortaleza",
            status_funil="inativo",
            responsavel_cadastro=self.usuario_a,
            consentimento_comunicacao=False,
        )
        self.client.force_login(self.usuario_a)
        resposta = self.client.get(reverse("eleitores:exportar"), {"formato": "csv"})
        self.assertEqual(resposta.status_code, 200)
        conteudo = resposta.content.decode("utf-8-sig")
        self.assertIn("Contato A", conteudo)
        self.assertNotIn("Contato B", conteudo)
        self.assertNotIn("Contato Sem Consentimento", conteudo)
        self.assertIn("attachment; filename=", resposta["Content-Disposition"])

    def test_api_lista_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.get("/api/v1/contatos/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["nome_completo"], "Contato A")

    def test_api_lista_interacoes_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.get("/api/v1/contato-interacoes/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["descricao"], "Primeiro contato telefonico")

    def test_api_lista_tarefas_isola_por_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.get("/api/v1/contato-tarefas/")
        self.assertEqual(resposta.status_code, 200)
        resultados = resposta.json()["results"]
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]["titulo"], "Retornar na sexta")

    def test_api_nao_permite_registrar_interacao_para_contato_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.post(
            "/api/v1/contato-interacoes/",
            {
                "contato": str(self.contato_b.pk),
                "tipo": "mensagem",
                "data_hora": "2026-07-29T11:00:00Z",
                "descricao": "Tentativa indevida",
                "responsavel": str(self.usuario_a.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_nao_permite_registrar_tarefa_para_contato_de_outra_campanha(self):
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.post(
            "/api/v1/contato-tarefas/",
            {
                "contato": str(self.contato_b.pk),
                "titulo": "Agendar retorno indevido",
                "prazo": "2026-07-30T12:00:00Z",
                "concluida": False,
                "responsavel": str(self.usuario_a.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_nao_permite_relacionar_lideranca_de_outra_campanha(self):
        lideranca_b = Lideranca.objects.create(
            campanha=self.campanha_b,
            nome_completo="Lideranca B",
            telefone="85988880000",
            tipo_lideranca="regional",
            estado="CE",
            cidade="Caucaia",
        )
        client = APIClient()
        client.force_authenticate(self.usuario_a)
        resposta = client.post(
            "/api/v1/contatos/",
            {
                "nome_completo": "Contato Novo",
                "telefone": "85933335555",
                "cidade": "Fortaleza",
                "status_funil": "novo_contato",
                "lideranca_relacionada": str(lideranca_b.pk),
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 400)

    def test_api_bloqueia_criacao_para_visualizador(self):
        client = APIClient()
        client.force_authenticate(self.visualizador_a)
        resposta = client.post(
            "/api/v1/contatos/",
            {
                "nome_completo": "Contato Somente Leitura",
                "telefone": "85977774444",
                "cidade": "Fortaleza",
                "status_funil": "novo_contato",
            },
            format="json",
        )
        self.assertEqual(resposta.status_code, 403)
