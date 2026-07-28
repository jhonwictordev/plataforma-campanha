from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from .permissions import (
    PermissaoObjetoCampanhaDRF,
    filtrar_queryset_por_usuario,
    usuario_tem_nivel,
)


class ViewSetCampanhaProtegido(viewsets.ModelViewSet):
    permission_classes = [PermissaoObjetoCampanhaDRF]
    niveis_permitidos: tuple[str, ...] = ()
    niveis_permitidos_leitura: tuple[str, ...] = ()
    niveis_permitidos_escrita: tuple[str, ...] = ()
    exigir_campanha = True
    campo_campanha = "campanha_id"

    def _obter_niveis_permitidos(self) -> tuple[str, ...]:
        if self.action in {"list", "retrieve"} and self.niveis_permitidos_leitura:
            return self.niveis_permitidos_leitura
        if self.action in {"create", "update", "partial_update", "destroy"} and self.niveis_permitidos_escrita:
            return self.niveis_permitidos_escrita
        return self.niveis_permitidos

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        niveis_permitidos = self._obter_niveis_permitidos()
        if niveis_permitidos and not usuario_tem_nivel(request.user, niveis_permitidos):
            raise PermissionDenied("Voce nao possui permissao para acessar este recurso.")
        if (
            self.exigir_campanha
            and not (request.user.is_superuser or request.user.is_staff)
            and not getattr(request.user, "campanha_id", None)
        ):
            raise PermissionDenied("Seu usuario precisa estar vinculado a uma campanha ativa.")

    def get_queryset(self):
        queryset = super().get_queryset()
        return filtrar_queryset_por_usuario(
            queryset=queryset,
            usuario=self.request.user,
            campo_campanha=self.campo_campanha,
            exigir_campanha=self.exigir_campanha,
        )

    def perform_create(self, serializer):
        usuario = self.request.user
        campanha_id = serializer.validated_data.get("campanha_id") or serializer.validated_data.get("campanha")
        if usuario.is_superuser or usuario.is_staff:
            serializer.save()
            return
        if not getattr(usuario, "campanha_id", None):
            raise PermissionDenied("Seu usuario precisa estar vinculado a uma campanha ativa.")
        if campanha_id and getattr(campanha_id, "id", campanha_id) != usuario.campanha_id:
            raise PermissionDenied("Nao e permitido criar registros em outra campanha.")
        serializer.save(campanha=usuario.campanha)


class ViewSetAnaliticoCampanhaProtegido(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    niveis_permitidos: tuple[str, ...] = ()
    exigir_campanha = True
    campo_campanha = "campanha_id"

    def usuario_admin(self) -> bool:
        usuario = self.request.user
        return bool(usuario.is_superuser or getattr(usuario, "is_staff", False))

    def campanha_selecionada_id(self):
        if self.usuario_admin():
            campanha_id = self.request.query_params.get("campanha", "").strip()
            return campanha_id or None
        return getattr(self.request.user, "campanha_id", None)

    def filtrar_queryset(self, queryset):
        if self.usuario_admin():
            campanha_id = self.campanha_selecionada_id()
            if campanha_id:
                return queryset.filter(**{self.campo_campanha: campanha_id})
            return queryset
        return filtrar_queryset_por_usuario(
            queryset=queryset,
            usuario=self.request.user,
            campo_campanha=self.campo_campanha,
            exigir_campanha=self.exigir_campanha,
        )

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.niveis_permitidos and not usuario_tem_nivel(request.user, self.niveis_permitidos):
            raise PermissionDenied("Voce nao possui permissao para acessar este recurso.")
        if self.exigir_campanha and not self.usuario_admin() and not getattr(request.user, "campanha_id", None):
            raise PermissionDenied("Seu usuario precisa estar vinculado a uma campanha ativa.")
