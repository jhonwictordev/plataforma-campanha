import re

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from core.permissions import PAPEIS_COORDENACAO

from .models import Campanha

Usuario = get_user_model()

PADRAO_COR_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


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

        queryset_coordenadores = Usuario.objects.filter(is_active=True, nivel_acesso__in=PAPEIS_COORDENACAO).order_by(
            "nome_completo",
            "email",
        )
        if self.instance.pk:
            queryset_coordenadores = queryset_coordenadores.filter(
                Q(campanha__isnull=True) | Q(campanha=self.instance) | Q(pk=self.instance.coordenador_responsavel_id)
            )
        else:
            queryset_coordenadores = queryset_coordenadores.filter(campanha__isnull=True)
        self.fields["coordenador_responsavel"].queryset = queryset_coordenadores.distinct()
        self.fields["coordenador_responsavel"].required = False

    def clean_cor_primaria(self):
        cor = self.cleaned_data["cor_primaria"]
        if cor and not PADRAO_COR_HEX.match(cor):
            raise forms.ValidationError("Informe uma cor hexadecimal valida no formato #RRGGBB.")
        return cor

    def clean_cor_secundaria(self):
        cor = self.cleaned_data["cor_secundaria"]
        if cor and not PADRAO_COR_HEX.match(cor):
            raise forms.ValidationError("Informe uma cor hexadecimal valida no formato #RRGGBB.")
        return cor

    def clean_coordenador_responsavel(self):
        coordenador = self.cleaned_data.get("coordenador_responsavel")
        if not coordenador:
            return coordenador

        campanha_id = getattr(coordenador, "campanha_id", None)
        if campanha_id and campanha_id != getattr(self.instance, "pk", None):
            raise forms.ValidationError("O coordenador selecionado ja esta vinculado a outra campanha.")
        return coordenador

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get("data_inicio")
        data_eleicao = cleaned_data.get("data_eleicao")

        if data_inicio and data_eleicao and data_eleicao < data_inicio:
            self.add_error("data_eleicao", "A data da eleicao nao pode ser anterior ao inicio da campanha.")

        return cleaned_data
