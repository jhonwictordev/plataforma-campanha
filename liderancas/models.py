from django.db import models

from core.models import ModeloCampanha


class Lideranca(ModeloCampanha):
    class Tipos(models.TextChoices):
        POLITICA = "politica", "Política"
        COMUNITARIA = "comunitaria", "Comunitária"
        RELIGIOSA = "religiosa", "Religiosa"
        EMPRESARIAL = "empresarial", "Empresarial"
        SINDICAL = "sindical", "Sindical"
        REGIONAL = "regional", "Regional"

    class NiveisInfluencia(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"
        ESTRATEGICA = "estrategica", "Estratégica"

    class Situacoes(models.TextChoices):
        NOVO_CONTATO = "novo_contato", "Novo contato"
        EM_NEGOCIACAO = "em_negociacao", "Em negociação"
        APOIADOR = "apoiador", "Apoiador"
        LIDERANCA_CONFIRMADA = "lideranca_confirmada", "Liderança confirmada"
        INDECISO = "indeciso", "Indeciso"
        SEM_INTERESSE = "sem_interesse", "Sem interesse"
        INATIVO = "inativo", "Inativo"

    nome_completo = models.CharField(max_length=255)
    nome_conhecido = models.CharField(max_length=120, blank=True)
    cpf = models.CharField(max_length=14, blank=True)
    telefone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    data_nascimento = models.DateField(blank=True, null=True)
    genero = models.CharField(max_length=30, blank=True)
    tipo_lideranca = models.CharField(max_length=20, choices=Tipos.choices, db_index=True)
    organizacao = models.CharField(max_length=255, blank=True)
    cargo_funcao = models.CharField(max_length=120, blank=True)
    estado = models.CharField(max_length=2, db_index=True)
    cidade = models.CharField(max_length=120, db_index=True)
    bairro = models.CharField(max_length=120, blank=True, db_index=True)
    endereco = models.CharField(max_length=255, blank=True)
    regiao_eleitoral = models.CharField(max_length=120, blank=True, db_index=True)
    zona_eleitoral = models.CharField(max_length=20, blank=True)
    secao_eleitoral = models.CharField(max_length=20, blank=True)
    apoiadores_estimados = models.PositiveIntegerField(default=0)
    nivel_influencia = models.CharField(max_length=20, choices=NiveisInfluencia.choices, default=NiveisInfluencia.MEDIA)
    responsavel_contato = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="liderancas_responsavel",
        null=True,
        blank=True,
    )
    situacao_relacionamento = models.CharField(
        max_length=25,
        choices=Situacoes.choices,
        default=Situacoes.NOVO_CONTATO,
        db_index=True,
    )
    data_ultimo_contato = models.DateTimeField(blank=True, null=True)
    proxima_acao = models.CharField(max_length=255, blank=True)
    observacoes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    foto = models.ImageField(upload_to="liderancas/fotos/", blank=True, null=True)
    consentimento_dados = models.BooleanField(default=False)
    data_consentimento = models.DateTimeField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        verbose_name = "Liderança"
        verbose_name_plural = "Lideranças"
        indexes = [
            models.Index(fields=["nome_completo"]),
            models.Index(fields=["telefone"]),
            models.Index(fields=["email"]),
            models.Index(fields=["cidade", "bairro"]),
        ]

    def __str__(self):
        return self.nome_conhecido or self.nome_completo


class InteracaoLideranca(ModeloCampanha):
    class Tipos(models.TextChoices):
        REUNIAO = "reuniao", "Reunião"
        LIGACAO = "ligacao", "Ligação"
        MENSAGEM = "mensagem", "Mensagem"
        VISITA = "visita", "Visita"
        COMPROMISSO = "compromisso", "Compromisso"

    lideranca = models.ForeignKey(Lideranca, on_delete=models.CASCADE, related_name="interacoes")
    tipo = models.CharField(max_length=20, choices=Tipos.choices)
    data_hora = models.DateTimeField()
    resumo = models.CharField(max_length=255)
    detalhes = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="interacoes_liderancas",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Interação com liderança"
        verbose_name_plural = "Interações com lideranças"
