from django import forms

from core.forms import FormularioBootstrapMixin

from .models import CategoriaFinanceira, CentroCusto, LancamentoFinanceiro, ParceiroFinanceiro


class CategoriaFinanceiraFormulario(FormularioBootstrapMixin):
    class Meta:
        model = CategoriaFinanceira
        fields = ["nome", "tipo"]


class CentroCustoFormulario(FormularioBootstrapMixin):
    class Meta:
        model = CentroCusto
        fields = ["nome", "codigo"]


class ParceiroFinanceiroFormulario(FormularioBootstrapMixin):
    class Meta:
        model = ParceiroFinanceiro
        fields = ["nome", "documento", "tipo", "telefone", "email"]


class LancamentoFinanceiroFormulario(FormularioBootstrapMixin):
    class Meta:
        model = LancamentoFinanceiro
        fields = [
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
        ]
        widgets = {
            "valor_reais": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "data_vencimento": forms.DateInput(attrs={"type": "date"}),
            "data_pagamento": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            campanha_id = usuario.campanha_id
            self.fields["categoria"].queryset = self.fields["categoria"].queryset.filter(campanha_id=campanha_id)
            self.fields["parceiro"].queryset = self.fields["parceiro"].queryset.filter(campanha_id=campanha_id)
            self.fields["responsavel_lancamento"].queryset = self.fields["responsavel_lancamento"].queryset.filter(
                campanha_id=campanha_id
            )
            self.fields["centro_custo"].queryset = self.fields["centro_custo"].queryset.filter(campanha_id=campanha_id)
            if not self.instance.pk:
                self.fields["responsavel_lancamento"].initial = usuario.pk

    def clean(self):
        dados = super().clean()
        tipo = dados.get("tipo")
        categoria = dados.get("categoria")
        parceiro = dados.get("parceiro")
        responsavel = dados.get("responsavel_lancamento")
        centro_custo = dados.get("centro_custo")
        valor = dados.get("valor_reais")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)

        if valor is not None and valor <= 0:
            self.add_error("valor_reais", "O valor deve ser maior que zero.")
        if categoria and tipo and categoria.tipo != tipo:
            self.add_error("categoria", "A categoria precisa ter o mesmo tipo do lancamento.")
        if campanha_id and parceiro and parceiro.campanha_id != campanha_id:
            self.add_error("parceiro", "O parceiro precisa pertencer a mesma campanha.")
        if campanha_id and responsavel and responsavel.campanha_id != campanha_id:
            self.add_error("responsavel_lancamento", "O responsavel precisa pertencer a mesma campanha.")
        if campanha_id and centro_custo and centro_custo.campanha_id != campanha_id:
            self.add_error("centro_custo", "O centro de custo precisa pertencer a mesma campanha.")

        return dados
