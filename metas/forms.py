from django import forms

from core.forms import FormularioBootstrapMixin

from .models import MetaCampanha


class MetaCampanhaFormulario(FormularioBootstrapMixin):
    class Meta:
        model = MetaCampanha
        fields = [
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
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "valor_esperado": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "valor_realizado": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "data_inicial": forms.DateInput(attrs={"type": "date"}),
            "data_final": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            campanha_id = usuario.campanha_id
            self.fields["responsavel"].queryset = self.fields["responsavel"].queryset.filter(campanha_id=campanha_id)
            self.fields["equipe"].queryset = self.fields["equipe"].queryset.filter(campanha_id=campanha_id)
            if not self.instance.pk:
                self.fields["responsavel"].initial = usuario.pk

    def clean(self):
        dados = super().clean()
        valor_esperado = dados.get("valor_esperado")
        valor_realizado = dados.get("valor_realizado")
        data_inicial = dados.get("data_inicial")
        data_final = dados.get("data_final")
        responsavel = dados.get("responsavel")
        equipe = dados.get("equipe")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)

        if valor_esperado is not None and valor_esperado <= 0:
            self.add_error("valor_esperado", "O valor esperado deve ser maior que zero.")
        if valor_realizado is not None and valor_realizado < 0:
            self.add_error("valor_realizado", "O valor realizado nao pode ser negativo.")
        if data_inicial and data_final and data_final < data_inicial:
            self.add_error("data_final", "A data final deve ser igual ou posterior a data inicial.")
        if campanha_id and responsavel and responsavel.campanha_id != campanha_id:
            self.add_error("responsavel", "O responsavel precisa pertencer a mesma campanha.")
        if campanha_id and equipe and equipe.campanha_id != campanha_id:
            self.add_error("equipe", "A equipe vinculada precisa pertencer a mesma campanha.")

        return dados
