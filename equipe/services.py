from .models import TarefaEquipe


def normalizar_checklist(valor: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if isinstance(valor, (list, tuple)):
        return [str(item).strip() for item in valor if str(item).strip()]
    if not valor:
        return []
    itens = []
    for linha in str(valor).splitlines():
        item = linha.strip().lstrip("-").lstrip("•").strip()
        if item:
            itens.append(item)
    return itens


def agrupar_tarefas_por_status(tarefas, status_choices):
    colunas = []
    tarefas_lista = list(tarefas)
    for valor, rotulo in status_choices:
        colunas.append(
            {
                "valor": valor,
                "rotulo": rotulo,
                "tarefas": [tarefa for tarefa in tarefas_lista if tarefa.status == valor],
            }
        )
    return colunas


def contar_tarefas_em_aberto(queryset):
    return queryset.exclude(status__in=[TarefaEquipe.Status.CONCLUIDO, TarefaEquipe.Status.CANCELADO]).count()
