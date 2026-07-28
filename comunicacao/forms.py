from django import forms

from core.forms import FormularioBootstrapMixin

from .models import (
    CampanhaComunicacao,
    CanalComunicacao,
    EnvioComunicacao,
    ListaBloqueio,
    ModeloMensagem,
    NotificacaoInterna,
)
from .services import analisar_destinatarios


class ModeloMensagemFormulario(FormularioBootstrapMixin):
    class Meta:
        model = ModeloMensagem
        fields = ["nome", "canal", "assunto", "conteudo"]
        widgets = {
            "conteudo": forms.Textarea(attrs={"rows": 6}),
        }


class ListaBloqueioFormulario(FormularioBootstrapMixin):
    class Meta:
        model = ListaBloqueio
        fields = ["contato", "canal", "motivo"]
        widgets = {
            "motivo": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            self.fields["contato"].queryset = self.fields["contato"].queryset.filter(campanha_id=usuario.campanha_id)

    def clean(self):
        dados = super().clean()
        contato = dados.get("contato")
        canal = dados.get("canal")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)
        if campanha_id and contato and contato.campanha_id != campanha_id:
            self.add_error("contato", "O contato precisa pertencer a mesma campanha.")
        if campanha_id and contato and canal:
            queryset = ListaBloqueio.objects.filter(campanha_id=campanha_id, contato=contato, canal=canal)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                self.add_error("contato", "Ja existe um bloqueio ativo para este contato e canal.")
        return dados


class CampanhaComunicacaoFormulario(FormularioBootstrapMixin):
    class Meta:
        model = CampanhaComunicacao
        fields = [
            "nome",
            "modelo_mensagem",
            "assunto",
            "conteudo",
            "canal",
            "destinatarios",
            "data_envio",
            "responsavel",
            "status",
            "permitir_cancelamento_inscricao",
            "observacoes_internas",
        ]
        widgets = {
            "conteudo": forms.Textarea(attrs={"rows": 7}),
            "destinatarios": forms.SelectMultiple(attrs={"size": 10}),
            "data_envio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "observacoes_internas": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        self.fields["destinatarios"].help_text = (
            "Selecione somente contatos com consentimento valido e canal autorizado."
        )
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            campanha_id = usuario.campanha_id
            self.fields["modelo_mensagem"].queryset = self.fields["modelo_mensagem"].queryset.filter(
                campanha_id=campanha_id
            )
            self.fields["destinatarios"].queryset = self.fields["destinatarios"].queryset.filter(campanha_id=campanha_id)
            self.fields["responsavel"].queryset = self.fields["responsavel"].queryset.filter(campanha_id=campanha_id)
            if not self.instance.pk:
                self.fields["responsavel"].initial = usuario.pk

    def clean(self):
        dados = super().clean()
        modelo = dados.get("modelo_mensagem")
        canal = dados.get("canal")
        destinatarios = dados.get("destinatarios")
        responsavel = dados.get("responsavel")
        status = dados.get("status")
        data_envio = dados.get("data_envio")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)

        if modelo and not dados.get("assunto") and modelo.assunto:
            dados["assunto"] = modelo.assunto
            self.cleaned_data["assunto"] = modelo.assunto
        if modelo and not dados.get("conteudo"):
            dados["conteudo"] = modelo.conteudo
            self.cleaned_data["conteudo"] = modelo.conteudo

        if status == CampanhaComunicacao.Status.AGENDADA and not data_envio:
            self.add_error("data_envio", "Informe a data e hora para agendar a comunicacao.")
        if status == CampanhaComunicacao.Status.AGENDADA and not destinatarios:
            self.add_error("destinatarios", "Selecione ao menos um destinatario para agendar a campanha.")
        if campanha_id and responsavel and responsavel.campanha_id != campanha_id:
            self.add_error("responsavel", "O responsavel precisa pertencer a mesma campanha.")
        if campanha_id and modelo and modelo.campanha_id != campanha_id:
            self.add_error("modelo_mensagem", "O modelo precisa pertencer a mesma campanha.")
        if campanha_id and canal and destinatarios:
            erros = analisar_destinatarios(campanha_id=campanha_id, canal=canal, destinatarios=destinatarios)
            if erros.get("outra_campanha"):
                self.add_error("destinatarios", "Existem destinatarios vinculados a outra campanha.")
            if erros.get("sem_consentimento"):
                self.add_error("destinatarios", "Existem destinatarios sem consentimento valido.")
            if erros.get("canal_nao_autorizado"):
                self.add_error("destinatarios", "Existem destinatarios sem autorizacao para o canal selecionado.")
            if erros.get("bloqueados"):
                self.add_error("destinatarios", "Existem destinatarios presentes na lista de bloqueio.")
        return dados


class EnvioComunicacaoFormulario(FormularioBootstrapMixin):
    class Meta:
        model = EnvioComunicacao
        fields = [
            "status",
            "mensagem_enviada",
            "erro_envio",
            "resposta_recebida",
            "cancelou_inscricao",
            "observacoes_internas",
        ]
        widgets = {
            "mensagem_enviada": forms.Textarea(attrs={"rows": 4}),
            "resposta_recebida": forms.Textarea(attrs={"rows": 4}),
            "observacoes_internas": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        dados = super().clean()
        status = dados.get("status")
        if status == EnvioComunicacao.Status.FALHA and not dados.get("erro_envio"):
            self.add_error("erro_envio", "Informe a falha registrada para este envio.")
        if status == EnvioComunicacao.Status.RESPONDIDO and not dados.get("resposta_recebida"):
            self.add_error("resposta_recebida", "Informe a resposta recebida do destinatario.")
        return dados


class NotificacaoInternaFiltroFormulario(forms.Form):
    categoria = forms.ChoiceField(choices=[("", "Todas")] + list(NotificacaoInterna.Categorias.choices), required=False)
    status = forms.ChoiceField(
        choices=[("", "Todas"), ("nao_lidas", "Nao lidas"), ("lidas", "Lidas")],
        required=False,
    )
    busca = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.Select):
                campo.widget.attrs["class"] = "form-select"
            else:
                campo.widget.attrs["class"] = "form-control"
            campo.widget.attrs.setdefault("placeholder", campo.label)


class RegistroWebhookFiltroFormulario(forms.Form):
    canal = forms.ChoiceField(choices=[("", "Todos")] + list(CanalComunicacao.choices), required=False)
    assinatura = forms.ChoiceField(
        choices=[("", "Todas"), ("valida", "Assinatura valida"), ("invalida", "Assinatura invalida")],
        required=False,
    )
    processamento = forms.ChoiceField(
        choices=[("", "Todos"), ("processado", "Processado"), ("pendente", "Nao processado")],
        required=False,
    )
    provedor = forms.CharField(required=False)
    evento = forms.CharField(required=False)
    busca = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.Select):
                campo.widget.attrs["class"] = "form-select"
            else:
                campo.widget.attrs["class"] = "form-control"
            campo.widget.attrs.setdefault("placeholder", campo.label)
