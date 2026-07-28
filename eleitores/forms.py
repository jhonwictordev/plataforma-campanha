from django import forms
from django.utils import timezone

from core.forms import FormularioBootstrapMixin, normalizar_tags

from .models import ContatoCRM, InteracaoContato, TarefaContato


class ContatoCRMFormulario(FormularioBootstrapMixin):
    tags_texto = forms.CharField(
        label="Tags",
        required=False,
        help_text="Informe tags separadas por vírgula.",
    )

    class Meta:
        model = ContatoCRM
        fields = [
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
            "lideranca_relacionada",
            "status_funil",
            "tags_texto",
            "observacoes",
            "data_primeiro_contato",
            "data_ultimo_contato",
            "proxima_acao",
            "consentimento_comunicacao",
            "canal_autorizado",
            "data_consentimento",
            "latitude",
            "longitude",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}),
            "data_primeiro_contato": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_ultimo_contato": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "data_consentimento": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        self.fields["tags_texto"].initial = ", ".join(getattr(self.instance, "tags", []) or [])
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            self.fields["lideranca_relacionada"].queryset = self.fields["lideranca_relacionada"].queryset.filter(
                campanha_id=usuario.campanha_id
            )

    def clean_tags_texto(self):
        return normalizar_tags(self.cleaned_data.get("tags_texto"))

    def clean(self):
        dados = super().clean()
        campanha_id = getattr(self.usuario, "campanha_id", None)
        telefone = dados.get("telefone")
        email = dados.get("email")
        if campanha_id and (telefone or email):
            queryset = ContatoCRM.todos_objetos.filter(campanha_id=campanha_id)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            duplicado = queryset.filter(telefone=telefone).exists()
            if email:
                duplicado = duplicado or queryset.filter(email=email).exists()
            dados["possivel_duplicado"] = duplicado
        if dados.get("consentimento_comunicacao") and not dados.get("data_consentimento"):
            dados["data_consentimento"] = timezone.now()
        return dados

    def save(self, commit=True):
        instancia = super().save(commit=False)
        instancia.tags = self.cleaned_data.get("tags_texto", [])
        instancia.possivel_duplicado = self.cleaned_data.get("possivel_duplicado", False)
        if self.usuario and not instancia.responsavel_cadastro_id:
            instancia.responsavel_cadastro = self.usuario
        if commit:
            instancia.save()
        return instancia


class FormularioSimplesBootstrapMixin(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, (forms.Select, forms.SelectMultiple)):
                campo.widget.attrs.setdefault("class", "form-select")
            else:
                campo.widget.attrs.setdefault("class", "form-control")
            if not isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs.setdefault("placeholder", campo.label)


class ImportacaoContatoCRMFormulario(FormularioSimplesBootstrapMixin):
    arquivo = forms.FileField(
        label="Arquivo",
        help_text="Envie um arquivo CSV ou XLSX com os contatos do CRM.",
    )
    atualizar_existentes = forms.BooleanField(
        label="Atualizar contatos ja existentes",
        required=False,
        help_text="Quando marcado, contatos com o mesmo telefone ou e-mail serao atualizados.",
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        nome = (arquivo.name or "").lower()
        if not (nome.endswith(".csv") or nome.endswith(".xlsx")):
            raise forms.ValidationError("Envie um arquivo CSV ou XLSX.")
        return arquivo


class ExportacaoContatoCRMFormulario(FormularioSimplesBootstrapMixin):
    formato = forms.ChoiceField(
        label="Formato",
        choices=(
            ("csv", "CSV"),
            ("xlsx", "Excel"),
        ),
    )


class InteracaoContatoFormulario(FormularioBootstrapMixin):
    class Meta:
        model = InteracaoContato
        fields = ["tipo", "data_hora", "descricao", "responsavel"]
        widgets = {
            "data_hora": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            self.fields["responsavel"].queryset = self.fields["responsavel"].queryset.filter(
                campanha_id=usuario.campanha_id
            )
            if not self.instance.pk:
                self.fields["responsavel"].initial = usuario.pk

    def clean(self):
        dados = super().clean()
        responsavel = dados.get("responsavel")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)
        if campanha_id and responsavel and responsavel.campanha_id != campanha_id:
            self.add_error("responsavel", "O responsavel precisa pertencer a mesma campanha.")
        return dados


class TarefaContatoFormulario(FormularioBootstrapMixin):
    class Meta:
        model = TarefaContato
        fields = ["titulo", "prazo", "concluida", "responsavel"]
        widgets = {
            "prazo": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            self.fields["responsavel"].queryset = self.fields["responsavel"].queryset.filter(
                campanha_id=usuario.campanha_id
            )
            if not self.instance.pk:
                self.fields["responsavel"].initial = usuario.pk

    def clean(self):
        dados = super().clean()
        responsavel = dados.get("responsavel")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)
        if campanha_id and responsavel and responsavel.campanha_id != campanha_id:
            self.add_error("responsavel", "O responsavel precisa pertencer a mesma campanha.")
        return dados
