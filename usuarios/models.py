from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UsuarioManager


class Usuario(AbstractUser):
    class NiveisAcesso(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        COORDENADOR_GERAL = "coordenador_geral", "Coordenador-geral"
        COORDENADOR_REGIONAL = "coordenador_regional", "Coordenador regional"
        FINANCEIRO = "financeiro", "Financeiro"
        COMUNICACAO = "comunicacao", "Comunicação"
        MOBILIZADOR = "mobilizador", "Mobilizador"
        VOLUNTARIO = "voluntario", "Voluntário"
        VISUALIZADOR = "visualizador", "Visualizador"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("e-mail", unique=True)
    nome_completo = models.CharField(max_length=255)
    nome_exibicao = models.CharField(max_length=120, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    foto_perfil = models.ImageField(upload_to="usuarios/fotos/", blank=True, null=True)
    campanha = models.ForeignKey(
        "campanhas.Campanha",
        on_delete=models.SET_NULL,
        related_name="usuarios_vinculados",
        null=True,
        blank=True,
    )
    nivel_acesso = models.CharField(
        max_length=30,
        choices=NiveisAcesso.choices,
        default=NiveisAcesso.VISUALIZADOR,
        db_index=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ultimo_acesso_registrado = models.DateTimeField(blank=True, null=True)
    ultimo_ip = models.GenericIPAddressField(blank=True, null=True)
    tentativas_falhas = models.PositiveIntegerField(default=0)
    dois_fatores_habilitado = models.BooleanField(default=False)
    tema_escuro = models.BooleanField(default=False)
    consentimento_privacidade = models.BooleanField(default=False)
    data_consentimento_privacidade = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    objects = UsuarioManager()

    class Meta(AbstractUser.Meta):
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["nivel_acesso"]),
            models.Index(fields=["campanha"]),
        ]

    def __str__(self):
        return self.nome_completo or self.email

    def save(self, *args, **kwargs):
        if not self.nome_exibicao:
            self.nome_exibicao = self.nome_completo.split(" ")[0] if self.nome_completo else self.email
        super().save(*args, **kwargs)

    @property
    def nome_primeiro(self):
        return self.nome_exibicao or self.nome_completo
