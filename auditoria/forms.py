from datetime import timedelta

from django import forms
from django.utils import timezone

from campanhas.models import Campanha
from usuarios.models import Usuario

from .models import PoliticaRetencaoDados, SolicitacaoTitularDados


class AuditoriaFiltroFormulario(forms.Form):
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
    usuario = forms.ModelChoiceField(label="Usuario", queryset=Usuario.objects.none(), required=False)
    acao = forms.CharField(label="Acao", max_length=50, required=False)
    modelo = forms.CharField(label="Modelo", max_length=120, required=False)
    evento = forms.CharField(label="Evento", max_length=80, required=False)
    severidade = forms.ChoiceField(
        label="Severidade",
        required=False,
        choices=(
            ("", "Todas"),
            ("info", "Info"),
            ("aviso", "Aviso"),
            ("critico", "Critico"),
        ),
    )
    busca = forms.CharField(label="Busca", max_length=120, required=False)

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.eh_admin = usuario.is_superuser or getattr(usuario, "is_staff", False)

        hoje = timezone.localdate()
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

        usuarios_queryset = Usuario.objects.order_by("nome_completo", "pk")
        if not self.eh_admin:
            usuarios_queryset = usuarios_queryset.filter(campanha_id=getattr(usuario, "campanha_id", None))
        elif campanha_id:
            usuarios_queryset = usuarios_queryset.filter(campanha_id=campanha_id)
        self.fields["usuario"].queryset = usuarios_queryset

        for campo in self.fields.values():
            classes = "form-select" if isinstance(campo.widget, (forms.Select, forms.SelectMultiple)) else "form-control"
            campo.widget.attrs.setdefault("class", classes)

    def clean(self):
        cleaned = super().clean()
        data_inicial = cleaned.get("data_inicial") or self.initial["data_inicial"]
        data_final = cleaned.get("data_final") or self.initial["data_final"]
        if data_inicial > data_final:
            self.add_error("data_final", "A data final precisa ser maior ou igual a data inicial.")
        return cleaned

    def dados_resolvidos(self):
        if self.is_bound:
            self.is_valid()
        cleaned = getattr(self, "cleaned_data", {})
        campanha = cleaned.get("campanha")
        campanha_id = str(campanha.pk) if campanha else ""
        if not self.eh_admin:
            campanha_id = str(getattr(self.usuario, "campanha_id", "") or "")

        usuario = cleaned.get("usuario")
        return {
            "campanha_id": campanha_id,
            "data_inicial": cleaned.get("data_inicial") or self.initial["data_inicial"],
            "data_final": cleaned.get("data_final") or self.initial["data_final"],
            "usuario_id": str(usuario.pk) if usuario else "",
            "acao": (cleaned.get("acao") or "").strip(),
            "modelo": (cleaned.get("modelo") or "").strip(),
            "evento": (cleaned.get("evento") or "").strip(),
            "severidade": cleaned.get("severidade") or "",
            "busca": (cleaned.get("busca") or "").strip(),
        }


class PoliticaRetencaoDadosFormulario(forms.ModelForm):
    class Meta:
        model = PoliticaRetencaoDados
        fields = [
            "campanha",
            "nome",
            "tipo_registro",
            "base_legal",
            "dias_retencao",
            "dias_ate_anonimizacao",
            "anonimizar_ao_expirar",
            "responsavel",
            "observacoes",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.eh_admin = usuario.is_superuser or getattr(usuario, "is_staff", False)
        campanha_id = ""
        if self.is_bound:
            campanha_id = (self.data.get("campanha") or "").strip()
        elif getattr(self.instance, "campanha_id", None):
            campanha_id = str(self.instance.campanha_id)

        if self.eh_admin:
            self.fields["campanha"].queryset = Campanha.objects.order_by("nome_campanha", "nome_candidato")
        else:
            self.fields.pop("campanha")

        responsaveis = Usuario.objects.order_by("nome_completo", "pk")
        if self.eh_admin and campanha_id:
            responsaveis = responsaveis.filter(campanha_id=campanha_id)
        elif not self.eh_admin:
            responsaveis = responsaveis.filter(campanha_id=getattr(usuario, "campanha_id", None))
        self.fields["responsavel"].queryset = responsaveis

        for campo in self.fields.values():
            classes = "form-select" if isinstance(campo.widget, (forms.Select, forms.SelectMultiple)) else "form-control"
            campo.widget.attrs.setdefault("class", classes)


class SolicitacaoTitularDadosFormulario(forms.ModelForm):
    executar_acao_lgpd = forms.BooleanField(
        required=False,
        label="Executar a acao automatica ao concluir",
    )

    class Meta:
        model = SolicitacaoTitularDados
        fields = [
            "campanha",
            "nome_solicitante",
            "email_solicitante",
            "telefone_solicitante",
            "canal_origem",
            "tipo_solicitacao",
            "status",
            "descricao",
            "contato_relacionado",
            "lideranca_relacionada",
            "responsavel_interno",
            "prazo_resposta",
            "resposta_interna",
        ]
        widgets = {
            "prazo_resposta": forms.DateInput(attrs={"type": "date"}),
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "resposta_interna": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.eh_admin = usuario.is_superuser or getattr(usuario, "is_staff", False)
        campanha_id = ""
        if self.is_bound:
            campanha_id = (self.data.get("campanha") or "").strip()
        elif getattr(self.instance, "campanha_id", None):
            campanha_id = str(self.instance.campanha_id)
        elif getattr(usuario, "campanha_id", None):
            campanha_id = str(usuario.campanha_id)

        if self.eh_admin:
            self.fields["campanha"].queryset = Campanha.objects.order_by("nome_campanha", "nome_candidato")
        else:
            self.fields.pop("campanha")

        responsaveis = Usuario.objects.order_by("nome_completo", "pk")
        if self.eh_admin and campanha_id:
            responsaveis = responsaveis.filter(campanha_id=campanha_id)
        elif not self.eh_admin:
            responsaveis = responsaveis.filter(campanha_id=getattr(usuario, "campanha_id", None))
        self.fields["responsavel_interno"].queryset = responsaveis

        from eleitores.models import ContatoCRM
        from liderancas.models import Lideranca

        contatos = ContatoCRM.objects.order_by("nome_completo", "pk")
        liderancas = Lideranca.objects.order_by("nome_completo", "pk")
        if self.eh_admin and campanha_id:
            contatos = contatos.filter(campanha_id=campanha_id)
            liderancas = liderancas.filter(campanha_id=campanha_id)
        elif not self.eh_admin:
            contatos = contatos.filter(campanha_id=getattr(usuario, "campanha_id", None))
            liderancas = liderancas.filter(campanha_id=getattr(usuario, "campanha_id", None))
        self.fields["contato_relacionado"].queryset = contatos
        self.fields["lideranca_relacionada"].queryset = liderancas

        for campo in self.fields.values():
            classes = "form-select" if isinstance(campo.widget, (forms.Select, forms.SelectMultiple)) else "form-control"
            campo.widget.attrs.setdefault("class", classes)
        self.fields["executar_acao_lgpd"].widget.attrs.setdefault("class", "form-check-input")

    def clean(self):
        cleaned = super().clean()
        contato = cleaned.get("contato_relacionado")
        lideranca = cleaned.get("lideranca_relacionada")
        campanha = cleaned.get("campanha") if self.eh_admin else getattr(self.usuario, "campanha", None)
        if contato and campanha and contato.campanha_id != campanha.id:
            self.add_error("contato_relacionado", "O contato precisa pertencer a mesma campanha.")
        if lideranca and campanha and lideranca.campanha_id != campanha.id:
            self.add_error("lideranca_relacionada", "A lideranca precisa pertencer a mesma campanha.")
        if not contato and not lideranca and cleaned.get("executar_acao_lgpd"):
            self.add_error("executar_acao_lgpd", "Vincule um contato ou lideranca para executar a acao automatica.")
        return cleaned
