from rest_framework import serializers

from .forms import RelatorioFiltroFormulario
from .models import FiltroFavoritoRelatorio
from .services import (
    filters_to_querystring,
    obter_relatorios_disponiveis,
    serialize_filters,
    usuario_admin,
    validar_tipo_relatorio,
)


class RelatorioRespostaSerializer(serializers.Serializer):
    filtros = serializers.JSONField()
    campanha_atual = serializers.JSONField(allow_null=True)
    campanhas_disponiveis = serializers.JSONField()
    responsaveis = serializers.JSONField()
    relatorios_disponiveis = serializers.JSONField()
    relatorio = serializers.JSONField()
    total_linhas = serializers.IntegerField()
    mostrar_filtro_campanha = serializers.BooleanField()


class FiltroFavoritoRelatorioSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)
    filtros_querystring = serializers.SerializerMethodField()

    class Meta:
        model = FiltroFavoritoRelatorio
        fields = [
            "id",
            "campanha",
            "nome",
            "tipo_relatorio",
            "filtros",
            "filtros_querystring",
            "usuario",
            "usuario_nome",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "usuario", "usuario_nome", "filtros_querystring", "criado_em", "atualizado_em")
        extra_kwargs = {
            "campanha": {"required": False},
        }

    def get_filtros_querystring(self, obj):
        return filters_to_querystring(obj.filtros or {})

    def validate(self, attrs):
        request = self.context["request"]
        usuario = request.user
        tipo_relatorio = attrs.get("tipo_relatorio") or getattr(self.instance, "tipo_relatorio", "")
        filtros = attrs.get("filtros") or getattr(self.instance, "filtros", {}) or {}
        campanha = attrs.get("campanha") or getattr(self.instance, "campanha", None)
        relatorios_disponiveis = obter_relatorios_disponiveis(usuario)

        validar_tipo_relatorio(usuario, tipo_relatorio, relatorios_disponiveis)

        if not usuario_admin(usuario):
            campanha = usuario.campanha
            attrs["campanha"] = campanha
        elif campanha is None:
            raise serializers.ValidationError({"campanha": "Selecione uma campanha para salvar o filtro favorito."})

        payload_formulario = {
            "tipo_relatorio": tipo_relatorio,
            "campanha": str(getattr(campanha, "pk", campanha) or filtros.get("campanha", "")),
            "data_inicial": filtros.get("data_inicial", ""),
            "data_final": filtros.get("data_final", ""),
            "cidade": filtros.get("cidade", ""),
            "bairro": filtros.get("bairro", ""),
            "responsavel": filtros.get("responsavel", ""),
        }
        formulario = RelatorioFiltroFormulario(
            data=payload_formulario,
            usuario=usuario,
            relatorios_disponiveis=relatorios_disponiveis,
        )
        if not formulario.is_valid():
            raise serializers.ValidationError(formulario.errors)

        filtros_resolvidos = formulario.dados_resolvidos()
        filtros_normalizados = serialize_filters(filtros_resolvidos)
        filtros_normalizados["tipo_relatorio"] = tipo_relatorio

        attrs["tipo_relatorio"] = tipo_relatorio
        attrs["filtros"] = filtros_normalizados

        return attrs

    def create(self, validated_data):
        validated_data["usuario"] = self.context["request"].user
        return super().create(validated_data)
