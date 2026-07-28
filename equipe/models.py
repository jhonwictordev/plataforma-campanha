from django.db import models

from core.models import ModeloCampanha


class IntegranteEquipe(ModeloCampanha):
    nome = models.CharField(max_length=255)
    foto = models.ImageField(upload_to="equipe/fotos/", blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    funcao = models.CharField(max_length=120)
    departamento = models.CharField(max_length=120, db_index=True)
    cidade_regiao = models.CharField(max_length=120, blank=True, db_index=True)
    responsavel_direto = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="subordinados",
        null=True,
        blank=True,
    )
    data_entrada = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, default="ativo")
    disponibilidade = models.CharField(max_length=120, blank=True)
    observacoes = models.TextField(blank=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="cadastro_equipe",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.nome


class TarefaEquipe(ModeloCampanha):
    class Status(models.TextChoices):
        A_FAZER = "a_fazer", "A fazer"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        EM_REVISAO = "em_revisao", "Em revisão"
        CONCLUIDO = "concluido", "Concluído"
        CANCELADO = "cancelado", "Cancelado"

    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        IntegranteEquipe,
        on_delete=models.SET_NULL,
        related_name="tarefas",
        null=True,
        blank=True,
    )
    prazo = models.DateTimeField(blank=True, null=True)
    prioridade = models.CharField(max_length=15, default="media")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.A_FAZER, db_index=True)
    checklist = models.JSONField(default=list, blank=True)
    comentarios = models.TextField(blank=True)

    class Meta:
        verbose_name = "Tarefa de equipe"
        verbose_name_plural = "Tarefas de equipe"

    def __str__(self):
        return self.titulo
