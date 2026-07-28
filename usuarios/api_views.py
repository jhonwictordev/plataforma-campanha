from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from auditoria.models import LogSeguranca
from core.api import ViewSetCampanhaProtegido
from core.permissions import PAPEIS_COORDENACAO
from usuarios.models import Usuario
from usuarios.serializers import (
    AlterarSenhaSerializer,
    PerfilUsuarioSerializer,
    TokenJWTUsuarioSerializer,
    UsuarioSerializer,
)


def registrar_log_usuario_api(usuario: Usuario, evento: str, descricao: str, request, severidade: str = "info") -> None:
    LogSeguranca.todos_objetos.create(
        campanha=usuario.campanha,
        usuario=usuario,
        evento=evento,
        severidade=severidade,
        descricao=descricao,
        endereco_ip=request.META.get("REMOTE_ADDR"),
    )


@extend_schema(
    tags=["Autenticacao"],
    summary="Obter token JWT",
    responses={200: OpenApiResponse(description="Token emitido com sucesso.")},
)
class TokenJWTUsuarioView(TokenObtainPairView):
    serializer_class = TokenJWTUsuarioSerializer


@extend_schema(
    tags=["Usuarios"],
    summary="Consultar perfil autenticado",
)
class MeuPerfilAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PerfilUsuarioSerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        usuario = serializer.save()
        registrar_log_usuario_api(
            usuario=usuario,
            evento="usuario_perfil_atualizado_api",
            descricao=f"Perfil atualizado via API para {usuario.email}.",
            request=self.request,
        )


@extend_schema(
    tags=["Usuarios"],
    summary="Alterar senha do usuario autenticado",
    request=AlterarSenhaSerializer,
    responses={200: OpenApiResponse(description="Senha alterada com sucesso.")},
)
class AlterarSenhaAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AlterarSenhaSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        registrar_log_usuario_api(
            usuario=usuario,
            evento="usuario_senha_alterada_api",
            descricao=f"Senha alterada via API para {usuario.email}.",
            request=request,
            severidade="aviso",
        )
        return Response({"detail": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(tags=["Usuarios"], summary="Listar usuarios da campanha"),
    retrieve=extend_schema(tags=["Usuarios"], summary="Detalhar usuario"),
    create=extend_schema(tags=["Usuarios"], summary="Criar usuario"),
    update=extend_schema(tags=["Usuarios"], summary="Atualizar usuario"),
    partial_update=extend_schema(tags=["Usuarios"], summary="Atualizar usuario parcialmente"),
    destroy=extend_schema(tags=["Usuarios"], summary="Desativar usuario"),
)
class UsuarioViewSet(ViewSetCampanhaProtegido):
    queryset = Usuario.objects.select_related("campanha").order_by("nome_completo", "email")
    serializer_class = UsuarioSerializer
    niveis_permitidos_leitura = PAPEIS_COORDENACAO
    niveis_permitidos_escrita = (
        Usuario.NiveisAcesso.ADMINISTRADOR,
        Usuario.NiveisAcesso.COORDENADOR_GERAL,
    )
    search_fields = ("nome_completo", "nome_exibicao", "email", "telefone")
    filterset_fields = ("campanha", "nivel_acesso", "is_active", "dois_fatores_habilitado")
    ordering_fields = ("nome_completo", "email", "criado_em", "ultimo_acesso_registrado")

    def get_queryset(self):
        queryset = super().get_queryset()
        usuario = self.request.user
        if usuario.is_superuser or usuario.is_staff:
            return queryset
        return queryset.filter(
            Q(pk=usuario.pk)
            | ~Q(
                nivel_acesso__in=[
                    Usuario.NiveisAcesso.ADMINISTRADOR,
                    Usuario.NiveisAcesso.COORDENADOR_GERAL,
                ]
            )
        )

    def update(self, request, *args, **kwargs):
        if str(kwargs.get("pk")) == str(request.user.pk):
            raise PermissionDenied("Use o endpoint de perfil para atualizar sua propria conta.")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if str(kwargs.get("pk")) == str(request.user.pk):
            raise PermissionDenied("Use o endpoint de perfil para atualizar sua propria conta.")
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        usuario = self.request.user
        serializer.save(campanha=serializer.validated_data.get("campanha") or usuario.campanha)
        alvo = serializer.instance
        registrar_log_usuario_api(
            usuario=usuario,
            evento="usuario_criado_api",
            descricao=f"Usuario {alvo.email} criado via API.",
            request=self.request,
        )

    def perform_update(self, serializer):
        if serializer.instance.pk == self.request.user.pk:
            raise PermissionDenied("Use o endpoint de perfil para atualizar sua propria conta.")
        serializer.save()
        registrar_log_usuario_api(
            usuario=self.request.user,
            evento="usuario_atualizado_api",
            descricao=f"Usuario {serializer.instance.email} atualizado via API.",
            request=self.request,
        )

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise PermissionDenied("Nao e permitido desativar a propria conta por este endpoint.")
        instance.is_active = False
        instance.save(update_fields=["is_active", "atualizado_em"])
        registrar_log_usuario_api(
            usuario=self.request.user,
            evento="usuario_desativado_api",
            descricao=f"Usuario {instance.email} desativado via API.",
            request=self.request,
            severidade="aviso",
        )
