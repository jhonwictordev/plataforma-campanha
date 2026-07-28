from django import forms

from .models import Campanha


class FormularioCampanha(forms.ModelForm):
    class Meta:
        model = Campanha
        fields = [
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
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_eleicao": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "objetivos_gerais": forms.Textarea(attrs={"rows": 4}),
            "cor_primaria": forms.TextInput(attrs={"type": "color"}),
            "cor_secundaria": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            classe = campo.widget.attrs.get("class", "")
            campo.widget.attrs["class"] = f"{classe} form-control".strip()
