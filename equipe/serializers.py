from rest_framework import serializers

from .models import IntegranteEquipe, TarefaEquipe


class IntegranteEquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegranteEquipe
        fields = [
            "id",
            "campanha",
            "nome",
            "foto",
            "telefone",
            "email",
            "funcao",
            "departamento",
            "cidade_regiao",
            "responsavel_direto",
            "data_entrada",
            "status",
            "disponibilidade",
            "observacoes",
            "usuario",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        responsavel_direto = attrs.get("responsavel_direto")
        usuario = attrs.get("usuario")

        if self.instance and responsavel_direto and responsavel_direto.pk == self.instance.pk:
            raise serializers.ValidationError(
                {"responsavel_direto": "O integrante nao pode ser responsavel direto de si mesmo."}
            )

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            if responsavel_direto and responsavel_direto.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel_direto": "O responsavel direto precisa pertencer a mesma campanha."}
                )
            if usuario and usuario.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"usuario": "O usuario vinculado precisa pertencer a mesma campanha."}
                )

        return attrs


class TarefaEquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarefaEquipe
        fields = [
            "id",
            "campanha",
            "titulo",
            "descricao",
            "responsavel",
            "prazo",
            "prioridade",
            "status",
            "checklist",
            "comentarios",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        responsavel = attrs.get("responsavel")

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            if responsavel and responsavel.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel": "O responsavel precisa pertencer a mesma campanha."}
                )

        return attrs
