from rest_framework import serializers

from .models import ContatoCRM, InteracaoContato, TarefaContato


class ContatoCRMSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContatoCRM
        fields = [
            "id",
            "campanha",
            "nome_completo",
            "telefone",
            "whatsapp",
            "email",
            "data_nascimento",
            "cidade",
            "bairro",
            "endereco",
            "zona_eleitoral",
            "secao_eleitoral",
            "origem_contato",
            "responsavel_cadastro",
            "lideranca_relacionada",
            "status_funil",
            "tags",
            "observacoes",
            "data_primeiro_contato",
            "data_ultimo_contato",
            "proxima_acao",
            "consentimento_comunicacao",
            "canal_autorizado",
            "data_consentimento",
            "possivel_duplicado",
            "latitude",
            "longitude",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em", "possivel_duplicado")

    def validate(self, attrs):
        usuario = self.context["request"].user
        lideranca = attrs.get("lideranca_relacionada")
        responsavel = attrs.get("responsavel_cadastro")
        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
            if responsavel and responsavel.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel_cadastro": "O responsavel precisa pertencer a mesma campanha."}
                )
            if lideranca and lideranca.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError(
                    {"lideranca_relacionada": "A lideranca relacionada precisa pertencer a mesma campanha."}
                )
            telefone = attrs.get("telefone") or getattr(self.instance, "telefone", None)
            email = attrs.get("email") or getattr(self.instance, "email", None)
            queryset = ContatoCRM.objects.filter(campanha=usuario.campanha)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            duplicado = queryset.filter(telefone=telefone).exists()
            if email:
                duplicado = duplicado or queryset.filter(email=email).exists()
            attrs["possivel_duplicado"] = duplicado
            attrs.setdefault("responsavel_cadastro", usuario)
        return attrs


class RelacionamentoContatoSerializerMixin(serializers.ModelSerializer):
    campo_contato = "contato"
    campo_responsavel = "responsavel"

    def validate(self, attrs):
        attrs = super().validate(attrs) if hasattr(super(), "validate") else attrs
        usuario = self.context["request"].user
        contato = attrs.get(self.campo_contato) or getattr(self.instance, self.campo_contato, None)
        responsavel = attrs.get(self.campo_responsavel) or getattr(self.instance, self.campo_responsavel, None)

        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
            if contato and contato.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError(
                    {self.campo_contato: "O contato precisa pertencer a mesma campanha."}
                )
            if responsavel and responsavel.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError(
                    {self.campo_responsavel: "O responsavel precisa pertencer a mesma campanha."}
                )
            attrs.setdefault("responsavel", usuario)
        return attrs


class InteracaoContatoSerializer(RelacionamentoContatoSerializerMixin):
    class Meta:
        model = InteracaoContato
        fields = [
            "id",
            "campanha",
            "contato",
            "tipo",
            "data_hora",
            "descricao",
            "responsavel",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")


class TarefaContatoSerializer(RelacionamentoContatoSerializerMixin):
    class Meta:
        model = TarefaContato
        fields = [
            "id",
            "campanha",
            "contato",
            "titulo",
            "prazo",
            "concluida",
            "responsavel",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")
