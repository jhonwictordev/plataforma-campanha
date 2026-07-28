from django.db import models

from core.models import ModeloBase


class Campanha(ModeloBase):
    class Cargos(models.TextChoices):
        PREFEITO = "prefeito", "Prefeito"
        VEREADOR = "vereador", "Vereador"
        DEPUTADO_ESTADUAL = "deputado_estadual", "Deputado estadual"
        DEPUTADO_FEDERAL = "deputado_federal", "Deputado federal"
        SENADOR = "senador", "Senador"
        GOVERNADOR = "governador", "Governador"
        PRESIDENTE = "presidente", "Presidente"
        OUTRO = "outro", "Outro"

    class Situacoes(models.TextChoices):
        PLANEJAMENTO = "planejamento", "Planejamento"
        ATIVA = "ativa", "Ativa"
        PAUSADA = "pausada", "Pausada"
        ENCERRADA = "encerrada", "Encerrada"

    nome_campanha = models.CharField(max_length=255)
    nome_candidato = models.CharField(max_length=255)
    cargo_disputado = models.CharField(max_length=30, choices=Cargos.choices, db_index=True)
    partido = models.CharField(max_length=20)
    numero_candidato = models.CharField(max_length=10)
    estado = models.CharField(max_length=2, db_index=True)
    municipio = models.CharField(max_length=120, db_index=True)
    data_inicio = models.DateField()
    data_eleicao = models.DateField()
    situacao = models.CharField(max_length=20, choices=Situacoes.choices, default=Situacoes.PLANEJAMENTO)
    foto_candidato = models.ImageField(upload_to="campanhas/candidato/", blank=True, null=True)
    logotipo = models.ImageField(upload_to="campanhas/logotipos/", blank=True, null=True)
    cor_primaria = models.CharField(max_length=7, default="#0F172A")
    cor_secundaria = models.CharField(max_length=7, default="#2563EB")
    coordenador_responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="campanhas_coordenadas",
        null=True,
        blank=True,
    )
    descricao = models.TextField(blank=True)
    objetivos_gerais = models.TextField(blank=True)

    class Meta:
        verbose_name = "Campanha"
        verbose_name_plural = "Campanhas"
        indexes = [
            models.Index(fields=["nome_campanha"]),
            models.Index(fields=["nome_candidato"]),
            models.Index(fields=["estado", "municipio"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["numero_candidato", "data_eleicao", "municipio"],
                name="campanha_numero_eleicao_municipio_unico",
            )
        ]

    def __str__(self):
        return f"{self.nome_campanha} - {self.nome_candidato}"
