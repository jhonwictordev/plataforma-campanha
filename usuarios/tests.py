from __future__ import annotations

from time import time

from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.test import APIClient

from campanhas.models import Campanha
from usuarios.models import Usuario


def gerar_token_totp(dispositivo: TOTPDevice) -> str:
    totp = TOTP(dispositivo.bin_key, dispositivo.step, dispositivo.t0, dispositivo.digits, dispositivo.drift)
    totp.time = time()
    return str(totp.token()).zfill(dispositivo.digits)


class DoisFatoresUsuarioTestCase(TestCase):
    def setUp(self):
        self.campanha = Campanha.objects.create(
            nome_campanha="Campanha Seguranca",
            nome_candidato="Candidata Seguranca",
            cargo_disputado="prefeito",
            partido="ABC",
            numero_candidato="12",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.usuario = Usuario.objects.create_user(
            email="seguranca@example.com",
            password="SenhaSegura2026!",
            nome_completo="Usuario Seguranca",
            campanha=self.campanha,
            nivel_acesso=Usuario.NiveisAcesso.COORDENADOR_GERAL,
        )

    def test_ativacao_2fa_gera_dispositivo_e_codigos_recuperacao(self):
        self.client.force_login(self.usuario)

        ativacao_url = reverse("usuarios:dois_fatores_ativar")
        response = self.client.get(ativacao_url)
        self.assertEqual(response.status_code, 200)

        dispositivo = TOTPDevice.objects.get(user=self.usuario, confirmed=False)
        token = gerar_token_totp(dispositivo)

        response = self.client.post(ativacao_url, {"token": token}, follow=True)
        self.assertEqual(response.status_code, 200)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.dois_fatores_habilitado)
        self.assertTrue(TOTPDevice.objects.filter(user=self.usuario, confirmed=True).exists())
        self.assertEqual(StaticDevice.objects.get(user=self.usuario).token_set.count(), 8)
        self.assertContains(response, "Guarde estes codigos em local seguro")

    def test_login_exige_segundo_fator_quando_habilitado(self):
        dispositivo = TOTPDevice.objects.create(
            user=self.usuario,
            name="Autenticador principal",
            confirmed=True,
        )
        self.usuario.dois_fatores_habilitado = True
        self.usuario.save(update_fields=["dois_fatores_habilitado", "atualizado_em"])

        response = self.client.post(
            reverse("login"),
            {"username": self.usuario.email, "password": "SenhaSegura2026!"},
            follow=False,
        )
        self.assertRedirects(response, reverse("login_2fa"), fetch_redirect_response=False)
        self.assertEqual(self.client.session.get("usuario_pre_2fa_id"), str(self.usuario.pk))

        token = gerar_token_totp(dispositivo)
        response = self.client.post(reverse("login_2fa"), {"token": token}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)

    def test_codigo_recuperacao_consome_token(self):
        TOTPDevice.objects.create(
            user=self.usuario,
            name="Autenticador principal",
            confirmed=True,
        )
        self.usuario.dois_fatores_habilitado = True
        self.usuario.save(update_fields=["dois_fatores_habilitado", "atualizado_em"])

        self.client.post(
            reverse("login"),
            {"username": self.usuario.email, "password": "SenhaSegura2026!"},
        )
        self.client.force_login(self.usuario)
        self.client.post(reverse("usuarios:dois_fatores_regenerar"), {"senha_atual": "SenhaSegura2026!"})
        self.client.logout()
        self.client.post(
            reverse("login"),
            {"username": self.usuario.email, "password": "SenhaSegura2026!"},
        )

        dispositivo = StaticDevice.objects.get(user=self.usuario)
        codigo = dispositivo.token_set.first().token

        response = self.client.post(reverse("login_2fa"), {"token": codigo}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertEqual(dispositivo.token_set.count(), 7)

    def test_desativacao_remove_dispositivos(self):
        self.client.force_login(self.usuario)
        dispositivo = TOTPDevice.objects.create(
            user=self.usuario,
            name="Autenticador principal",
            confirmed=True,
        )
        self.usuario.dois_fatores_habilitado = True
        self.usuario.save(update_fields=["dois_fatores_habilitado", "atualizado_em"])
        StaticDevice.objects.create(user=self.usuario, name="Codigos de recuperacao", confirmed=True)

        response = self.client.post(
            reverse("usuarios:dois_fatores_desativar"),
            {"senha_atual": "SenhaSegura2026!"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.dois_fatores_habilitado)
        self.assertFalse(TOTPDevice.objects.filter(pk=dispositivo.pk).exists())
        self.assertFalse(StaticDevice.objects.filter(user=self.usuario).exists())


class UsuariosAPITestCase(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.campanha_a = Campanha.objects.create(
            nome_campanha="Campanha API A",
            nome_candidato="Candidata API A",
            cargo_disputado="prefeito",
            partido="AAA",
            numero_candidato="10",
            estado="CE",
            municipio="Fortaleza",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.campanha_b = Campanha.objects.create(
            nome_campanha="Campanha API B",
            nome_candidato="Candidato API B",
            cargo_disputado="vereador",
            partido="BBB",
            numero_candidato="20",
            estado="CE",
            municipio="Caucaia",
            data_inicio="2026-07-01",
            data_eleicao="2026-10-04",
            situacao="ativa",
        )
        self.coordenador_geral = Usuario.objects.create_user(
            email="coord.api@example.com",
            password="SenhaSegura2026!",
            nome_completo="Coordenador API",
            campanha=self.campanha_a,
            nivel_acesso=Usuario.NiveisAcesso.COORDENADOR_GERAL,
        )
        self.usuario_mesma_campanha = Usuario.objects.create_user(
            email="voluntario.a@example.com",
            password="SenhaSegura2026!",
            nome_completo="Voluntario Campanha A",
            campanha=self.campanha_a,
            nivel_acesso=Usuario.NiveisAcesso.VOLUNTARIO,
        )
        self.usuario_outra_campanha = Usuario.objects.create_user(
            email="mobilizador.b@example.com",
            password="SenhaSegura2026!",
            nome_completo="Mobilizador Campanha B",
            campanha=self.campanha_b,
            nivel_acesso=Usuario.NiveisAcesso.MOBILIZADOR,
        )
        self.staff = Usuario.objects.create_user(
            email="staff.api@example.com",
            password="SenhaSegura2026!",
            nome_completo="Staff API",
            campanha=self.campanha_b,
            nivel_acesso=Usuario.NiveisAcesso.ADMINISTRADOR,
            is_staff=True,
        )

    def autenticar(self, usuario):
        self.client_api.force_authenticate(user=usuario)

    def test_api_token_jwt_retorna_usuario_autenticado(self):
        resposta = self.client_api.post(
            "/api/v1/auth/token/",
            {"email": self.coordenador_geral.email, "password": "SenhaSegura2026!"},
            format="json",
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("access", resposta.data)
        self.assertIn("refresh", resposta.data)
        self.assertEqual(resposta.data["usuario"]["email"], self.coordenador_geral.email)
        self.assertEqual(
            resposta.data["usuario"]["campanha"],
            str(self.campanha_a.pk),
        )

    def test_api_me_retorna_usuario_autenticado(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.get("/api/v1/usuarios/me/")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["email"], self.coordenador_geral.email)
        self.assertEqual(resposta.data["campanha_nome"], self.campanha_a.nome_campanha)

    def test_api_me_atualiza_perfil(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.patch(
            "/api/v1/usuarios/me/",
            {"nome_exibicao": "Coord", "tema_escuro": True},
            format="json",
        )

        self.assertEqual(resposta.status_code, 200)
        self.coordenador_geral.refresh_from_db()
        self.assertEqual(self.coordenador_geral.nome_exibicao, "Coord")
        self.assertTrue(self.coordenador_geral.tema_escuro)

    def test_api_alterar_senha_exige_senha_atual_valida(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.post(
            "/api/v1/usuarios/alterar-senha/",
            {
                "senha_atual": "SenhaErrada2026!",
                "nova_senha": "SenhaNova2026@",
                "confirmar_nova_senha": "SenhaNova2026@",
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("senha_atual", resposta.data)

    def test_api_alterar_senha_atualiza_credencial(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.post(
            "/api/v1/usuarios/alterar-senha/",
            {
                "senha_atual": "SenhaSegura2026!",
                "nova_senha": "SenhaNova2026@",
                "confirmar_nova_senha": "SenhaNova2026@",
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, 200)
        self.coordenador_geral.refresh_from_db()
        self.assertTrue(self.coordenador_geral.check_password("SenhaNova2026@"))

    def test_api_usuarios_lista_apenas_registros_da_mesma_campanha(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.get("/api/v1/usuarios/")

        self.assertEqual(resposta.status_code, 200)
        emails = {item["email"] for item in resposta.data["results"]}
        self.assertIn(self.coordenador_geral.email, emails)
        self.assertIn(self.usuario_mesma_campanha.email, emails)
        self.assertNotIn(self.usuario_outra_campanha.email, emails)

    def test_api_usuarios_bloqueia_idor_de_outra_campanha(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.get(f"/api/v1/usuarios/{self.usuario_outra_campanha.pk}/")

        self.assertEqual(resposta.status_code, 404)

    def test_api_coordenador_geral_cria_usuario_operacional_na_propria_campanha(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.post(
            "/api/v1/usuarios/",
            {
                "email": "financeiro.novo@example.com",
                "password": "SenhaInicial2026@",
                "nome_completo": "Financeiro Novo",
                "nivel_acesso": Usuario.NiveisAcesso.FINANCEIRO,
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, 201)
        novo_usuario = Usuario.objects.get(email="financeiro.novo@example.com")
        self.assertEqual(novo_usuario.campanha_id, self.campanha_a.id)
        self.assertEqual(novo_usuario.nivel_acesso, Usuario.NiveisAcesso.FINANCEIRO)

    def test_api_coordenador_geral_nao_pode_criar_administrador(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.post(
            "/api/v1/usuarios/",
            {
                "email": "admin.proibido@example.com",
                "password": "SenhaInicial2026@",
                "nome_completo": "Admin Proibido",
                "nivel_acesso": Usuario.NiveisAcesso.ADMINISTRADOR,
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertIn("nivel_acesso", resposta.data)

    def test_api_bloqueia_edicao_da_propria_conta_pelo_endpoint_administrativo(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.patch(
            f"/api/v1/usuarios/{self.coordenador_geral.pk}/",
            {"nome_completo": "Outro Nome"},
            format="json",
        )

        self.assertEqual(resposta.status_code, 403)

    def test_api_desativa_usuario_sem_excluir_registro(self):
        self.autenticar(self.coordenador_geral)

        resposta = self.client_api.delete(f"/api/v1/usuarios/{self.usuario_mesma_campanha.pk}/")

        self.assertEqual(resposta.status_code, 204)
        self.usuario_mesma_campanha.refresh_from_db()
        self.assertFalse(self.usuario_mesma_campanha.is_active)

    def test_api_staff_pode_criar_usuario_em_outra_campanha(self):
        self.autenticar(self.staff)

        resposta = self.client_api.post(
            "/api/v1/usuarios/",
            {
                "email": "regional.staff@example.com",
                "password": "SenhaInicial2026@",
                "nome_completo": "Regional Staff",
                "nivel_acesso": Usuario.NiveisAcesso.COORDENADOR_REGIONAL,
                "campanha": str(self.campanha_a.pk),
            },
            format="json",
        )

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(
            Usuario.objects.get(email="regional.staff@example.com").campanha_id,
            self.campanha_a.id,
        )
