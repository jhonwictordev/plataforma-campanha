from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from auditoria.models import LogSeguranca
from campanhas.models import Campanha
from usuarios.models import Usuario
from usuarios.policies import (
    PAPEIS_GERENCIAVEIS_GESTOR_LOCAL,
    papeis_gerenciaveis_por_usuario,
    usuario_admin_sistema,
)


class UsuarioResumoSerializer(serializers.ModelSerializer):
    campanha = serializers.UUIDField(source="campanha_id", read_only=True)
    campanha_nome = serializers.CharField(source="campanha.nome_campanha", read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nome_completo",
            "nome_exibicao",
            "nivel_acesso",
            "campanha",
            "campanha_nome",
            "foto_perfil",
            "tema_escuro",
            "dois_fatores_habilitado",
        )
        read_only_fields = fields


class TokenJWTUsuarioSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["nivel_acesso"] = user.nivel_acesso
        token["campanha_id"] = str(user.campanha_id) if user.campanha_id else None
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        usuario = self.user
        request = self.context.get("request")

        if not usuario.is_active:
            raise AuthenticationFailed("Esta conta esta inativa.")

        data["usuario"] = UsuarioResumoSerializer(usuario, context=self.context).data
        data["dois_fatores_habilitado"] = usuario.dois_fatores_habilitado

        LogSeguranca.todos_objetos.create(
            campanha=usuario.campanha,
            usuario=usuario,
            evento="api_jwt_emitido",
            severidade="info",
            descricao=f"Token JWT emitido para {usuario.email}.",
            endereco_ip=(request.META.get("REMOTE_ADDR") if request else None),
        )
        return data


class UsuarioSerializer(serializers.ModelSerializer):
    campanha = serializers.PrimaryKeyRelatedField(
        queryset=Campanha.objects.filter(excluido_em__isnull=True),
        required=False,
        allow_null=True,
        pk_field=serializers.UUIDField(format="hex_verbose"),
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, style={"input_type": "password"})
    campanha_nome = serializers.CharField(source="campanha.nome_campanha", read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nome_completo",
            "nome_exibicao",
            "telefone",
            "foto_perfil",
            "campanha",
            "campanha_nome",
            "nivel_acesso",
            "is_active",
            "dois_fatores_habilitado",
            "tema_escuro",
            "ultimo_acesso_registrado",
            "criado_em",
            "atualizado_em",
            "password",
        )
        read_only_fields = (
            "id",
            "dois_fatores_habilitado",
            "ultimo_acesso_registrado",
            "criado_em",
            "atualizado_em",
        )

    def validate_password(self, value):
        validate_password(value, self.instance or Usuario())
        return value

    def validate(self, attrs):
        request = self.context["request"]
        usuario_logado = request.user
        campanha = attrs.get("campanha", getattr(self.instance, "campanha", None))
        nivel_acesso = attrs.get("nivel_acesso", getattr(self.instance, "nivel_acesso", Usuario.NiveisAcesso.VISUALIZADOR))
        is_active = attrs.get("is_active", getattr(self.instance, "is_active", True))

        if usuario_admin_sistema(usuario_logado):
            return attrs

        if not usuario_logado.campanha_id:
            raise serializers.ValidationError("Seu usuario precisa estar vinculado a uma campanha para gerenciar contas.")

        if campanha and campanha.id != usuario_logado.campanha_id:
            raise serializers.ValidationError({"campanha": "Nao e permitido vincular usuarios a outra campanha."})

        if nivel_acesso not in papeis_gerenciaveis_por_usuario(usuario_logado):
            raise serializers.ValidationError(
                {"nivel_acesso": "Coordenadores-gerais so podem gerenciar perfis operacionais da propria campanha."}
            )

        if self.instance and self.instance.pk == usuario_logado.pk and not is_active:
            raise serializers.ValidationError({"is_active": "Use outra conta administrativa para desativar este usuario."})

        attrs["campanha"] = campanha or usuario_logado.campanha
        return attrs

    def create(self, validated_data):
        senha = validated_data.pop("password", None)
        if not senha:
            raise serializers.ValidationError({"password": "Informe uma senha inicial para o usuario."})
        usuario = Usuario(**validated_data)
        usuario.set_password(senha)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        senha = validated_data.pop("password", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if senha:
            instance.set_password(senha)
        instance.save()
        return instance


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    campanha = serializers.UUIDField(source="campanha_id", read_only=True)
    campanha_nome = serializers.CharField(source="campanha.nome_campanha", read_only=True)

    class Meta:
        model = Usuario
        fields = (
            "id",
            "email",
            "nome_completo",
            "nome_exibicao",
            "telefone",
            "foto_perfil",
            "tema_escuro",
            "nivel_acesso",
            "campanha",
            "campanha_nome",
            "dois_fatores_habilitado",
            "ultimo_acesso_registrado",
        )
        read_only_fields = (
            "id",
            "nivel_acesso",
            "campanha",
            "campanha_nome",
            "dois_fatores_habilitado",
            "ultimo_acesso_registrado",
        )


class AlterarSenhaSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True, style={"input_type": "password"})
    nova_senha = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirmar_nova_senha = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_senha_atual(self, value):
        usuario = self.context["request"].user
        if not usuario.check_password(value):
            raise serializers.ValidationError("A senha atual informada nao confere.")
        return value

    def validate(self, attrs):
        if attrs["nova_senha"] != attrs["confirmar_nova_senha"]:
            raise serializers.ValidationError({"confirmar_nova_senha": "A confirmacao de senha nao confere."})
        validate_password(attrs["nova_senha"], self.context["request"].user)
        return attrs

    def save(self, **kwargs):
        usuario = self.context["request"].user
        usuario.set_password(self.validated_data["nova_senha"])
        usuario.save(update_fields=["password", "atualizado_em"])
        return usuario
