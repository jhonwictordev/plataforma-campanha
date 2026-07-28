from core.views import ModuloPlaceholderView


class AuditoriaHomeView(ModuloPlaceholderView):
    extra_context = {
        "titulo": "Auditoria e segurança",
        "descricao": "Base inicial preparada para trilhas de auditoria, logs de segurança e governança por campanha.",
    }
