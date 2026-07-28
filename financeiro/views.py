from core.views import ModuloPlaceholderView


class FinanceiroHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Financeiro",
        "descricao": "Fundação criada para receitas, despesas, centros de custo, parceiros e prestação de contas auditável.",
    }
