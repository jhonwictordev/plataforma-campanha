from rest_framework import serializers

from .models import CategoriaFinanceira, CentroCusto, LancamentoFinanceiro, ParceiroFinanceiro


class CategoriaFinanceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaFinanceira
        fields = ["id", "campanha", "nome", "tipo", "criado_em", "atualizado_em"]
        read_only_fields = ("id", "criado_em", "atualizado_em")
        extra_kwargs = {"campanha": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})
        return attrs


class CentroCustoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroCusto
        fields = ["id", "campanha", "nome", "codigo", "criado_em", "atualizado_em"]
        read_only_fields = ("id", "criado_em", "atualizado_em")
        extra_kwargs = {"campanha": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})
        return attrs


class ParceiroFinanceiroSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParceiroFinanceiro
        fields = [
            "id",
            "campanha",
            "nome",
            "documento",
            "tipo",
            "telefone",
            "email",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")
        extra_kwargs = {"campanha": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})
        return attrs


class LancamentoFinanceiroSerializer(serializers.ModelSerializer):
    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "id",
            "campanha",
            "descricao",
            "tipo",
            "categoria",
            "valor_reais",
            "data_vencimento",
            "data_pagamento",
            "parceiro",
            "responsavel_lancamento",
            "centro_custo",
            "status",
            "forma_pagamento",
            "numero_documento",
            "comprovante",
            "observacoes",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")
        extra_kwargs = {"campanha": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        categoria = attrs.get("categoria", getattr(self.instance, "categoria", None))
        parceiro = attrs.get("parceiro", getattr(self.instance, "parceiro", None))
        responsavel = attrs.get("responsavel_lancamento", getattr(self.instance, "responsavel_lancamento", None))
        centro_custo = attrs.get("centro_custo", getattr(self.instance, "centro_custo", None))
        valor = attrs.get("valor_reais", getattr(self.instance, "valor_reais", None))

        if valor is not None and valor <= 0:
            raise serializers.ValidationError({"valor_reais": "O valor deve ser maior que zero."})
        if categoria and tipo and categoria.tipo != tipo:
            raise serializers.ValidationError({"categoria": "A categoria precisa ter o mesmo tipo do lancamento."})

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            if parceiro and parceiro.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError({"parceiro": "O parceiro precisa pertencer a mesma campanha."})
            if responsavel and responsavel.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel_lancamento": "O responsavel precisa pertencer a mesma campanha."}
                )
            if centro_custo and centro_custo.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"centro_custo": "O centro de custo precisa pertencer a mesma campanha."}
                )
            attrs.setdefault("responsavel_lancamento", usuario_logado)
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})

        return attrs
