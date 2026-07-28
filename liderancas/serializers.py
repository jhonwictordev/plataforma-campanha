from rest_framework import serializers

from .models import Lideranca


class LiderancaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lideranca
        fields = [
            "id",
            "campanha",
            "nome_completo",
            "nome_conhecido",
            "cpf",
            "telefone",
            "whatsapp",
            "email",
            "data_nascimento",
            "genero",
            "tipo_lideranca",
            "organizacao",
            "cargo_funcao",
            "estado",
            "cidade",
            "bairro",
            "endereco",
            "regiao_eleitoral",
            "zona_eleitoral",
            "secao_eleitoral",
            "apoiadores_estimados",
            "nivel_influencia",
            "responsavel_contato",
            "situacao_relacionamento",
            "data_ultimo_contato",
            "proxima_acao",
            "observacoes",
            "tags",
            "foto",
            "consentimento_dados",
            "data_consentimento",
            "latitude",
            "longitude",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario = self.context["request"].user
        responsavel = attrs.get("responsavel_contato")
        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
            if responsavel and responsavel.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel_contato": "O responsável precisa pertencer à mesma campanha."}
                )
            attrs.setdefault("responsavel_contato", usuario)
        return attrs
