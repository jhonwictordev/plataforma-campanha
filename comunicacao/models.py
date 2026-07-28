from django.db import models
from django.utils import timezone

from core.models import ModeloCampanha


class CanalComunicacao(models.TextChoices):
    EMAIL = "email", "E-mail"
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"
    NOTIFICACAO_INTERNA = "notificacao_interna", "Notificacao interna"


class ModeloMensagem(ModeloCampanha):
    nome = models.CharField(max_length=120)
    assunto = models.CharField(max_length=255, blank=True)
    conteudo = models.TextField()
    canal = models.CharField(max_length=30, choices=CanalComunicacao.choices, db_index=True)

    class Meta:
        verbose_name = "Modelo de mensagem"
        verbose_name_plural = "Modelos de mensagem"
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["canal"]),
        ]

    def __str__(self):
        return self.nome


class ListaBloqueio(ModeloCampanha):
    contato = models.ForeignKey(
        "eleitores.ContatoCRM",
        on_delete=models.CASCADE,
        related_name="bloqueios_comunicacao",
    )
    canal = models.CharField(max_length=30, choices=CanalComunicacao.choices, db_index=True)
    motivo = models.CharField(max_length=255, blank=True)
    solicitado_por = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="bloqueios_registrados",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Bloqueio de comunicacao"
        verbose_name_plural = "Bloqueios de comunicacao"
        indexes = [
            models.Index(fields=["canal"]),
            models.Index(fields=["contato", "canal"]),
        ]

    def __str__(self):
        return f"{self.contato} - {self.get_canal_display()}"


class CampanhaComunicacao(ModeloCampanha):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        AGENDADA = "agendada", "Agendada"
        ENVIANDO = "enviando", "Enviando"
        CONCLUIDA = "concluida", "Concluida"
        PAUSADA = "pausada", "Pausada"
        CANCELADA = "cancelada", "Cancelada"

    nome = models.CharField(max_length=255)
    assunto = models.CharField(max_length=255, blank=True)
    conteudo = models.TextField()
    canal = models.CharField(max_length=30, choices=CanalComunicacao.choices, db_index=True)
    modelo_mensagem = models.ForeignKey(
        ModeloMensagem,
        on_delete=models.SET_NULL,
        related_name="campanhas_comunicacao",
        null=True,
        blank=True,
    )
    destinatarios = models.ManyToManyField("eleitores.ContatoCRM", related_name="campanhas_comunicacao", blank=True)
    data_envio = models.DateTimeField(blank=True, null=True)
    responsavel = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="comunicacoes_responsavel",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO, db_index=True)
    permitir_cancelamento_inscricao = models.BooleanField(default=True)
    observacoes_internas = models.TextField(blank=True)
    quantidade_programada = models.PositiveIntegerField(default=0)
    quantidade_enviada = models.PositiveIntegerField(default=0)
    quantidade_entregue = models.PositiveIntegerField(default=0)
    quantidade_falha = models.PositiveIntegerField(default=0)
    quantidade_respostas = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Campanha de comunicacao"
        verbose_name_plural = "Campanhas de comunicacao"
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["canal", "status"]),
            models.Index(fields=["data_envio"]),
        ]

    def __str__(self):
        return self.nome

    def aplicar_modelo(self):
        if not self.modelo_mensagem_id:
            return
        if not self.assunto and self.modelo_mensagem.assunto:
            self.assunto = self.modelo_mensagem.assunto
        if not self.conteudo:
            self.conteudo = self.modelo_mensagem.conteudo

    def atualizar_metricas(self, salvar=True):
        envios = self.envios.order_by()
        self.quantidade_programada = envios.exclude(status=EnvioComunicacao.Status.CANCELADO).count()
        self.quantidade_enviada = envios.filter(
            status__in=[
                EnvioComunicacao.Status.ENVIADO,
                EnvioComunicacao.Status.ENTREGUE,
                EnvioComunicacao.Status.RESPONDIDO,
            ]
        ).count()
        self.quantidade_entregue = envios.filter(
            status__in=[
                EnvioComunicacao.Status.ENTREGUE,
                EnvioComunicacao.Status.RESPONDIDO,
            ]
        ).count()
        self.quantidade_falha = envios.filter(status=EnvioComunicacao.Status.FALHA).count()
        self.quantidade_respostas = envios.filter(status=EnvioComunicacao.Status.RESPONDIDO).count()
        if salvar:
            self.save(
                update_fields=[
                    "quantidade_programada",
                    "quantidade_enviada",
                    "quantidade_entregue",
                    "quantidade_falha",
                    "quantidade_respostas",
                    "atualizado_em",
                ]
            )

    def save(self, *args, **kwargs):
        self.aplicar_modelo()
        super().save(*args, **kwargs)


class EnvioComunicacao(ModeloCampanha):
    class Status(models.TextChoices):
        PROGRAMADO = "programado", "Programado"
        ENVIADO = "enviado", "Enviado"
        ENTREGUE = "entregue", "Entregue"
        FALHA = "falha", "Falha"
        RESPONDIDO = "respondido", "Respondido"
        CANCELADO = "cancelado", "Cancelado"

    campanha_comunicacao = models.ForeignKey(
        CampanhaComunicacao,
        on_delete=models.CASCADE,
        related_name="envios",
    )
    contato = models.ForeignKey(
        "eleitores.ContatoCRM",
        on_delete=models.CASCADE,
        related_name="envios_comunicacao",
    )
    canal = models.CharField(max_length=30, choices=CanalComunicacao.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROGRAMADO, db_index=True)
    mensagem_enviada = models.TextField(blank=True)
    erro_envio = models.CharField(max_length=255, blank=True)
    resposta_recebida = models.TextField(blank=True)
    data_programada = models.DateTimeField(blank=True, null=True)
    data_envio = models.DateTimeField(blank=True, null=True)
    data_entrega = models.DateTimeField(blank=True, null=True)
    data_resposta = models.DateTimeField(blank=True, null=True)
    cancelou_inscricao = models.BooleanField(default=False)
    observacoes_internas = models.TextField(blank=True)
    responsavel_registro = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="envios_comunicacao_registrados",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Envio de comunicacao"
        verbose_name_plural = "Envios de comunicacao"
        indexes = [
            models.Index(fields=["status", "canal"]),
            models.Index(fields=["campanha_comunicacao", "status"]),
            models.Index(fields=["contato", "canal"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["campanha_comunicacao", "contato"],
                name="comunicacao_envio_unico_por_contato",
            )
        ]

    def __str__(self):
        return f"{self.campanha_comunicacao} - {self.contato}"

    def save(self, *args, **kwargs):
        if self.campanha_comunicacao_id:
            self.campanha_id = self.campanha_comunicacao.campanha_id
            if not self.canal:
                self.canal = self.campanha_comunicacao.canal
        agora = timezone.now()
        if self.status in {self.Status.ENVIADO, self.Status.ENTREGUE, self.Status.RESPONDIDO} and not self.data_envio:
            self.data_envio = agora
        if self.status in {self.Status.ENTREGUE, self.Status.RESPONDIDO} and not self.data_entrega:
            self.data_entrega = agora
        if self.status == self.Status.RESPONDIDO and not self.data_resposta:
            self.data_resposta = agora
        super().save(*args, **kwargs)


class NotificacaoInterna(ModeloCampanha):
    class Categorias(models.TextChoices):
        AGENDA = "agenda", "Agenda"
        COMUNICACAO = "comunicacao", "Comunicacao"
        EQUIPE = "equipe", "Equipe"
        FINANCEIRO = "financeiro", "Financeiro"
        LGPD = "lgpd", "LGPD"
        RETENCAO = "retencao", "Retencao"
        SISTEMA = "sistema", "Sistema"

    usuario_destinatario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="notificacoes_internas",
    )
    titulo = models.CharField(max_length=160)
    mensagem = models.TextField()
    categoria = models.CharField(max_length=20, choices=Categorias.choices, default=Categorias.SISTEMA, db_index=True)
    url_destino = models.CharField(max_length=255, blank=True)
    origem_modelo = models.CharField(max_length=120, blank=True)
    origem_id = models.CharField(max_length=64, blank=True)
    chave_unica = models.CharField(max_length=140, blank=True, null=True)
    enviada_em = models.DateTimeField(default=timezone.now)
    lida_em = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        verbose_name = "Notificacao interna"
        verbose_name_plural = "Notificacoes internas"
        indexes = [
            models.Index(fields=["usuario_destinatario", "lida_em"]),
            models.Index(fields=["categoria", "criado_em"]),
            models.Index(fields=["origem_modelo", "origem_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["campanha", "usuario_destinatario", "chave_unica"],
                name="comunicacao_notificacao_chave_unica",
            )
        ]

    def __str__(self):
        return f"{self.usuario_destinatario} - {self.titulo}"

    @property
    def foi_lida(self) -> bool:
        return self.lida_em is not None

    def marcar_como_lida(self, salvar: bool = True):
        if self.lida_em:
            return self
        self.lida_em = timezone.now()
        if salvar:
            self.save(update_fields=["lida_em", "atualizado_em"])
        return self
