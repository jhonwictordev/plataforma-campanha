PAPEIS_GESTAO_USUARIOS = ("administrador", "coordenador_geral")
PAPEIS_GERENCIAVEIS_GESTOR_LOCAL = (
    "coordenador_regional",
    "financeiro",
    "comunicacao",
    "mobilizador",
    "voluntario",
    "visualizador",
)
PAPEIS_USUARIO_SISTEMA = (
    "administrador",
    "coordenador_geral",
    "coordenador_regional",
    "financeiro",
    "comunicacao",
    "mobilizador",
    "voluntario",
    "visualizador",
)


def usuario_admin_sistema(usuario) -> bool:
    return bool(getattr(usuario, "is_superuser", False) or getattr(usuario, "is_staff", False))


def usuario_pode_gerir_usuarios(usuario) -> bool:
    if not getattr(usuario, "is_authenticated", False):
        return False
    return usuario_admin_sistema(usuario) or getattr(usuario, "nivel_acesso", None) in PAPEIS_GESTAO_USUARIOS


def usuario_pode_gerir_multicampanha(usuario) -> bool:
    return usuario_admin_sistema(usuario)


def papeis_gerenciaveis_por_usuario(usuario) -> tuple[str, ...]:
    if usuario_admin_sistema(usuario):
        return PAPEIS_USUARIO_SISTEMA
    if getattr(usuario, "nivel_acesso", None) in PAPEIS_GESTAO_USUARIOS:
        return PAPEIS_GERENCIAVEIS_GESTOR_LOCAL
    return ()
