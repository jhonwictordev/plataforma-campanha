from django.db import models

from core.models import ModeloCampanha


class ContatoCRM(ModeloCampanha):
    class EtapasFunil(models.TextChoices):
        NOVO_CONTATO = "novo_contato", "Novo contato"
        PRIMEIRO_ATENDIMENTO = "primeiro_atendimento", "Primeiro atendimento"
        EM_RELACIONAMENTO = "em_relacionamento", "Em relacionamento"
        INTERESSADO = "interessado", "Interessado"
        APOIADOR = "apoiador", "Apoiador"
        VOLUNTARIO = "voluntario", "Voluntário"
        LIDERANCA = "lideranca", "Liderança"
        INATIVO = "inativo", "Inativo"

    nome_completo = models.CharField(max_length=255)
    telefone = models.CharField(max_length=20, db_index=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, db_index=True)
    data_nascimento = models.DateField(blank=True, null=True)
    cidade = models.CharField(max_length=120, db_index=True)
    bairro = models.CharField(max_length=120, blank=True, db_index=True)
    endereco = models.CharField(max_length=255, blank=True)
    zona_eleitoral = models.CharField(max_length=20, blank=True)
    secao_eleitoral = models.CharField(max_length=20, blank=True)
    origem_contato = models.CharField(max_length=120, blank=True, db_index=True)
    responsavel_cadastro = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="contatos_cadastrados",
        null=True,
        blank=True,
    )
    lideranca_relacionada = models.ForeignKey(
        "liderancas.Lideranca",
        on_delete=models.SET_NULL,
        related_name="contatos_relacionados",
        null=True,
        blank=True,
    )
    status_funil = models.CharField(max_length=25, choices=EtapasFunil.choices, default=EtapasFunil.NOVO_CONTATO)
    tags = models.JSONField(default=list, blank=True)
    observacoes = models.TextField(blank=True)
    data_primeiro_contato = models.DateTimeField(blank=True, null=True)
    data_ultimo_contato = models.DateTimeField(blank=True, null=True)
    proxima_acao = models.CharField(max_length=255, blank=True)
    consentimento_comunicacao = models.BooleanField(default=False)
    canal_autorizado = models.CharField(max_length=40, blank=True)
    data_consentimento = models.DateTimeField(blank=True, null=True)
    possivel_duplicado = models.BooleanField(default=False)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        verbose_name = "Contato CRM"
        verbose_name_plural = "Contatos CRM"
        indexes = [
            models.Index(fields=["nome_completo"]),
            models.Index(fields=["telefone", "email"]),
            models.Index(fields=["cidade", "bairro"]),
        ]

    def __str__(self):
        return self.nome_completo


class InteracaoContato(ModeloCampanha):
    contato = models.ForeignKey(ContatoCRM, on_delete=models.CASCADE, related_name="interacoes")
    tipo = models.CharField(max_length=50)
    data_hora = models.DateTimeField()
    descricao = models.TextField()
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="interacoes_contatos",
        null=True,
        blank=True,
    )


class TarefaContato(ModeloCampanha):
    contato = models.ForeignKey(ContatoCRM, on_delete=models.CASCADE, related_name="tarefas")
    titulo = models.CharField(max_length=255)
    prazo = models.DateTimeField(blank=True, null=True)
    concluida = models.BooleanField(default=False)
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="tarefas_contato",
        null=True,
        blank=True,
    )
