from core.views import ModuloPlaceholderView
from core.permissions import PAPEIS_AUDITORIA


class AuditoriaHomeView(ModuloPlaceholderView):
    niveis_permitidos = PAPEIS_AUDITORIA
    extra_context = {
        "titulo": "Auditoria e segurança",
        "descricao": "Base inicial preparada para trilhas de auditoria, logs de segurança e governança por campanha.",
    }
