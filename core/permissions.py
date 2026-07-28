from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

PAPEIS_COORDENACAO = ("administrador", "coordenador_geral", "coordenador_regional")
PAPEIS_TODOS_MODULOS = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "financeiro",
    "comunicacao",
    "mobilizador",
    "voluntario",
    "visualizador",
)
PAPEIS_CRM = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "comunicacao",
    "mobilizador",
    "visualizador",
)
PAPEIS_CRM_LEITURA = PAPEIS_CRM
PAPEIS_CRM_ESCRITA = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "comunicacao",
    "mobilizador",
)
PAPEIS_AGENDA = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "comunicacao",
    "mobilizador",
    "voluntario",
    "visualizador",
)
PAPEIS_AGENDA_LEITURA = PAPEIS_AGENDA
PAPEIS_AGENDA_ESCRITA = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "comunicacao",
    "mobilizador",
)
PAPEIS_EQUIPE = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "mobilizador",
    "visualizador",
)
PAPEIS_EQUIPE_LEITURA = PAPEIS_EQUIPE
PAPEIS_EQUIPE_ESCRITA = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "mobilizador",
)
PAPEIS_METAS_LEITURA = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "financeiro",
    "comunicacao",
    "mobilizador",
    "visualizador",
)
PAPEIS_METAS_ESCRITA = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "financeiro",
    "comunicacao",
    "mobilizador",
)
PAPEIS_FINANCEIRO = ("administrador", "coordenador_geral", "financeiro")
PAPEIS_FINANCEIRO_LEITURA = PAPEIS_FINANCEIRO
PAPEIS_FINANCEIRO_ESCRITA = PAPEIS_FINANCEIRO
PAPEIS_COMUNICACAO = ("administrador", "coordenador_geral", "coordenador_regional", "comunicacao")
PAPEIS_AUDITORIA = ("administrador", "coordenador_geral")


def usuario_tem_nivel(usuario, niveis_permitidos: tuple[str, ...] | set[str] | list[str]) -> bool:
    if not getattr(usuario, "is_authenticated", False):
        return False
    if usuario.is_superuser or getattr(usuario, "is_staff", False):
        return True
    if not niveis_permitidos:
        return True
    return getattr(usuario, "nivel_acesso", None) in set(niveis_permitidos)


def usuario_pode_visualizar_campanha(usuario, campanha_id) -> bool:
    if not getattr(usuario, "is_authenticated", False):
        return False
    if usuario.is_superuser or getattr(usuario, "is_staff", False):
        return True
    return getattr(usuario, "campanha_id", None) == campanha_id


def filtrar_queryset_por_usuario(queryset, usuario, campo_campanha: str = "campanha_id", exigir_campanha: bool = True):
    if not getattr(usuario, "is_authenticated", False):
        return queryset.none()
    if usuario.is_superuser or getattr(usuario, "is_staff", False):
        return queryset
    campanha_id = getattr(usuario, "campanha_id", None)
    if exigir_campanha and not campanha_id:
        return queryset.none()
    if not hasattr(queryset.model, campo_campanha):
        return queryset.none()
    return queryset.filter(**{campo_campanha: campanha_id})


def validar_acesso_objeto(usuario, objeto) -> None:
    campanha_id = getattr(objeto, "campanha_id", None)
    if campanha_id is None:
        return
    if not usuario_pode_visualizar_campanha(usuario, campanha_id):
        raise PermissionDenied("Você não possui acesso a registros de outra campanha.")


class PermissaoObjetoCampanhaDRF(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "is_authenticated", False)

    def has_object_permission(self, request, view, obj):
        campanha_id = getattr(obj, "campanha_id", None)
        if campanha_id is None:
            return True
        return usuario_pode_visualizar_campanha(request.user, campanha_id)
