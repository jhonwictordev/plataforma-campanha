def usuario_pode_visualizar_campanha(usuario, campanha_id) -> bool:
    if not getattr(usuario, "is_authenticated", False):
        return False
    if usuario.is_superuser or getattr(usuario, "is_staff", False):
        return True
    return getattr(usuario, "campanha_id", None) == campanha_id
