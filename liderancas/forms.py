from django import forms
from django.utils import timezone

from core.forms import FormularioBootstrapMixin, normalizar_tags

from .models import Lideranca


class LiderancaFormulario(FormularioBootstrapMixin):
    tags_texto = forms.CharField(
        label="Tags",
        required=False,
        help_text="Informe tags separadas por vírgula.",
    )

    class Meta:
        model = Lideranca
        fields = [
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
            "tags_texto",
            "foto",
            "consentimento_dados",
            "data_consentimento",
            "latitude",
            "longitude",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "data_ultimo_contato": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_consentimento": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        self.fields["tags_texto"].initial = ", ".join(getattr(self.instance, "tags", []) or [])
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            self.fields["responsavel_contato"].queryset = self.fields["responsavel_contato"].queryset.filter(
                campanha_id=usuario.campanha_id
            )

    def clean_tags_texto(self):
        return normalizar_tags(self.cleaned_data.get("tags_texto"))

    def clean(self):
        dados = super().clean()
        if dados.get("consentimento_dados") and not dados.get("data_consentimento"):
            dados["data_consentimento"] = timezone.now()
        return dados

    def save(self, commit=True):
        instancia = super().save(commit=False)
        instancia.tags = self.cleaned_data.get("tags_texto", [])
        if self.usuario and not instancia.responsavel_contato_id:
            instancia.responsavel_contato = self.usuario
        if commit:
            instancia.save()
        return instancia
