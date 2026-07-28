from django.db.models import Max


def sincronizar_ultimo_contato_lideranca(lideranca):
    ultima_interacao = lideranca.interacoes.aggregate(data_mais_recente=Max("data_hora"))["data_mais_recente"]
    if lideranca.data_ultimo_contato != ultima_interacao:
        lideranca.data_ultimo_contato = ultima_interacao
        lideranca.save(update_fields=["data_ultimo_contato", "atualizado_em"])
    return ultima_interacao
