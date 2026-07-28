from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_FINANCEIRO


class FinanceiroHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_FINANCEIRO
    extra_context = {
        "titulo": "Financeiro",
        "descricao": "Fundação criada para receitas, despesas, centros de custo, parceiros e prestação de contas auditável.",
    }
