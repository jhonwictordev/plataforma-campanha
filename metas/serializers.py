from rest_framework import serializers

from .models import MetaCampanha


class MetaCampanhaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaCampanha
        fields = [
            "id",
            "campanha",
            "nome",
            "descricao",
            "tipo",
            "valor_esperado",
            "valor_realizado",
            "data_inicial",
            "data_final",
            "responsavel",
            "equipe",
            "regiao",
            "status",
            "percentual_conclusao",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "percentual_conclusao", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        valor_esperado = attrs.get("valor_esperado", getattr(self.instance, "valor_esperado", None))
        valor_realizado = attrs.get("valor_realizado", getattr(self.instance, "valor_realizado", None))
        data_inicial = attrs.get("data_inicial", getattr(self.instance, "data_inicial", None))
        data_final = attrs.get("data_final", getattr(self.instance, "data_final", None))
        responsavel = attrs.get("responsavel", getattr(self.instance, "responsavel", None))
        equipe = attrs.get("equipe", getattr(self.instance, "equipe", None))

        if valor_esperado is not None and valor_esperado <= 0:
            raise serializers.ValidationError({"valor_esperado": "O valor esperado deve ser maior que zero."})
        if valor_realizado is not None and valor_realizado < 0:
            raise serializers.ValidationError({"valor_realizado": "O valor realizado nao pode ser negativo."})
        if data_inicial and data_final and data_final < data_inicial:
            raise serializers.ValidationError(
                {"data_final": "A data final deve ser igual ou posterior a data inicial."}
            )

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            if responsavel and responsavel.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel": "O responsavel precisa pertencer a mesma campanha."}
                )
            if equipe and equipe.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"equipe": "A equipe vinculada precisa pertencer a mesma campanha."}
                )
            attrs.setdefault("responsavel", usuario_logado)

        return attrs
