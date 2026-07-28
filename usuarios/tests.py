from __future__ import annotations

from time import time

from django.test import TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

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
