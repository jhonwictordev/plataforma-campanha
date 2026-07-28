import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.permissions import PAPEIS_COORDENACAO

from .models import Campanha

Usuario = get_user_model()

PADRAO_COR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class CampanhaSerializer(serializers.ModelSerializer):
    total_usuarios_vinculados = serializers.SerializerMethodField()
    total_contatos = serializers.SerializerMethodField()
    total_liderancas = serializers.SerializerMethodField()

    class Meta:
        model = Campanha
        fields = [
            "id",
            "nome_campanha",
            "nome_candidato",
            "cargo_disputado",
            "partido",
            "numero_candidato",
            "estado",
            "municipio",
            "data_inicio",
            "data_eleicao",
            "situacao",
            "foto_candidato",
            "logotipo",
            "cor_primaria",
            "cor_secundaria",
            "coordenador_responsavel",
            "descricao",
            "objetivos_gerais",
            "total_usuarios_vinculados",
            "total_contatos",
            "total_liderancas",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = (
            "id",
            "total_usuarios_vinculados",
            "total_contatos",
            "total_liderancas",
            "criado_em",
            "atualizado_em",
        )
        extra_kwargs = {
            "coordenador_responsavel": {"required": False, "allow_null": True},
            "descricao": {"required": False, "allow_blank": True},
            "objetivos_gerais": {"required": False, "allow_blank": True},
        }

    def get_total_usuarios_vinculados(self, obj) -> int:
        return obj.usuarios_vinculados.filter(is_active=True).count()

    def get_total_contatos(self, obj) -> int:
        return obj.contatocrms.count()

    def get_total_liderancas(self, obj) -> int:
        return obj.liderancas.count()

    def validate_cor_primaria(self, valor):
        if valor and not PADRAO_COR_HEX.match(valor):
            raise serializers.ValidationError("Informe uma cor hexadecimal valida no formato #RRGGBB.")
        return valor

    def validate_cor_secundaria(self, valor):
        if valor and not PADRAO_COR_HEX.match(valor):
            raise serializers.ValidationError("Informe uma cor hexadecimal valida no formato #RRGGBB.")
        return valor

    def validate_coordenador_responsavel(self, coordenador):
        if not coordenador:
            return coordenador
        if not (coordenador.is_superuser or getattr(coordenador, "is_staff", False)):
            if coordenador.nivel_acesso not in PAPEIS_COORDENACAO:
                raise serializers.ValidationError("Selecione um usuario com perfil de coordenacao.")
            campanha_atual = getattr(self.instance, "pk", None)
            if coordenador.campanha_id and coordenador.campanha_id != campanha_atual:
                raise serializers.ValidationError("O coordenador selecionado ja esta vinculado a outra campanha.")
        return coordenador

    def validate(self, attrs):
        data_inicio = attrs.get("data_inicio", getattr(self.instance, "data_inicio", None))
        data_eleicao = attrs.get("data_eleicao", getattr(self.instance, "data_eleicao", None))
        if data_inicio and data_eleicao and data_eleicao < data_inicio:
            raise serializers.ValidationError(
                {"data_eleicao": "A data da eleicao nao pode ser anterior ao inicio da campanha."}
            )
        return attrs

    def _sincronizar_coordenador(self, campanha):
        coordenador = campanha.coordenador_responsavel
        if (
            coordenador
            and not (coordenador.is_superuser or getattr(coordenador, "is_staff", False))
            and coordenador.campanha_id != campanha.pk
        ):
            coordenador.campanha = campanha
            coordenador.save(update_fields=["campanha", "atualizado_em"])

    def create(self, validated_data):
        campanha = super().create(validated_data)
        self._sincronizar_coordenador(campanha)
        return campanha

    def update(self, instance, validated_data):
        campanha = super().update(instance, validated_data)
        self._sincronizar_coordenador(campanha)
        return campanha
