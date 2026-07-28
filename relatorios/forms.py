from datetime import timedelta

from django import forms
from django.utils import timezone

from campanhas.models import Campanha
from usuarios.models import Usuario

from .models import FiltroFavoritoRelatorio


class RelatorioFiltroFormulario(forms.Form):
    tipo_relatorio = forms.ChoiceField(label="Relatorio")
    campanha = forms.ModelChoiceField(label="Campanha", queryset=Campanha.objects.none(), required=False)
    data_inicial = forms.DateField(
        label="Data inicial",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    data_final = forms.DateField(
        label="Data final",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    cidade = forms.CharField(label="Cidade", max_length=120, required=False)
    bairro = forms.CharField(label="Bairro", max_length=120, required=False)
    responsavel = forms.ModelChoiceField(label="Responsavel", queryset=Usuario.objects.none(), required=False)

    def __init__(self, *args, usuario, relatorios_disponiveis, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.relatorios_disponiveis = relatorios_disponiveis
        self.eh_admin = usuario.is_superuser or getattr(usuario, "is_staff", False)

        choices = [(item["chave"], item["rotulo"]) for item in relatorios_disponiveis]
        self.fields["tipo_relatorio"].choices = choices

        hoje = timezone.localdate()
        self.initial.setdefault("tipo_relatorio", choices[0][0] if choices else "")
        self.initial.setdefault("data_final", hoje)
        self.initial.setdefault("data_inicial", hoje - timedelta(days=29))

        campanha_id = ""
        if self.is_bound:
            campanha_id = (self.data.get("campanha") or "").strip()
        elif self.initial.get("campanha"):
            campanha_id = str(self.initial.get("campanha"))

        if self.eh_admin:
            self.fields["campanha"].queryset = Campanha.objects.order_by("nome_campanha", "nome_candidato")
        else:
            self.fields.pop("campanha")
            campanha_id = str(getattr(usuario, "campanha_id", "") or "")

        queryset_responsaveis = Usuario.objects.order_by("nome_completo", "pk")
        if not self.eh_admin:
            queryset_responsaveis = queryset_responsaveis.filter(campanha_id=getattr(usuario, "campanha_id", None))
        elif campanha_id:
            queryset_responsaveis = queryset_responsaveis.filter(campanha_id=campanha_id)
        self.fields["responsavel"].queryset = queryset_responsaveis

        for nome, campo in self.fields.items():
            classes = "form-select" if isinstance(campo.widget, (forms.Select, forms.SelectMultiple)) else "form-control"
            campo.widget.attrs.setdefault("class", classes)

    def clean(self):
        cleaned = super().clean()
        data_final = cleaned.get("data_final") or self.initial["data_final"]
        data_inicial = cleaned.get("data_inicial") or self.initial["data_inicial"]
        if data_inicial > data_final:
            self.add_error("data_final", "A data final precisa ser maior ou igual a data inicial.")
        return cleaned

    def dados_resolvidos(self):
        if self.is_bound:
            self.is_valid()

        cleaned = getattr(self, "cleaned_data", {})
        relatorio = cleaned.get("tipo_relatorio") or self.initial.get("tipo_relatorio", "")
        data_inicial = cleaned.get("data_inicial") or self.initial["data_inicial"]
        data_final = cleaned.get("data_final") or self.initial["data_final"]
        cidade = (cleaned.get("cidade") or "").strip()
        bairro = (cleaned.get("bairro") or "").strip()
        responsavel = cleaned.get("responsavel")

        campanha_id = ""
        campanha = cleaned.get("campanha")
        if campanha:
            campanha_id = str(campanha.pk)
        elif not self.eh_admin and getattr(self.usuario, "campanha_id", None):
            campanha_id = str(self.usuario.campanha_id)

        return {
            "tipo_relatorio": relatorio,
            "campanha_id": campanha_id,
            "data_inicial": data_inicial,
            "data_final": data_final,
            "cidade": cidade,
            "bairro": bairro,
            "responsavel_id": str(responsavel.pk) if responsavel else "",
        }


class FiltroFavoritoRelatorioFormulario(forms.ModelForm):
    class Meta:
        model = FiltroFavoritoRelatorio
        fields = ["nome"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: Contatos Fortaleza - julho",
                }
            ),
        }
