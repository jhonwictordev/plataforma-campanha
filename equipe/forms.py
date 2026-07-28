from django import forms

from core.forms import FormularioBootstrapMixin

from .models import IntegranteEquipe, TarefaEquipe
from .services import normalizar_checklist


class IntegranteEquipeFormulario(FormularioBootstrapMixin):
    class Meta:
        model = IntegranteEquipe
        fields = [
            "nome",
            "foto",
            "telefone",
            "email",
            "funcao",
            "departamento",
            "cidade_regiao",
            "responsavel_direto",
            "data_entrada",
            "status",
            "disponibilidade",
            "observacoes",
            "usuario",
        ]
        widgets = {
            "data_entrada": forms.DateInput(attrs={"type": "date"}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            campanha_id = usuario.campanha_id
            self.fields["responsavel_direto"].queryset = self.fields["responsavel_direto"].queryset.filter(
                campanha_id=campanha_id
            )
            self.fields["usuario"].queryset = self.fields["usuario"].queryset.filter(campanha_id=campanha_id)

    def clean(self):
        dados = super().clean()
        responsavel_direto = dados.get("responsavel_direto")
        usuario = dados.get("usuario")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)

        if self.instance.pk and responsavel_direto and responsavel_direto.pk == self.instance.pk:
            self.add_error("responsavel_direto", "O integrante nao pode ser responsavel direto de si mesmo.")

        if campanha_id and responsavel_direto and responsavel_direto.campanha_id != campanha_id:
            self.add_error("responsavel_direto", "O responsavel direto precisa pertencer a mesma campanha.")

        if campanha_id and usuario and usuario.campanha_id != campanha_id:
            self.add_error("usuario", "O usuario vinculado precisa pertencer a mesma campanha.")

        return dados


class TarefaEquipeFormulario(FormularioBootstrapMixin):
    checklist_texto = forms.CharField(
        label="Checklist",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Informe um item por linha para acompanhar a execucao da tarefa.",
    )

    class Meta:
        model = TarefaEquipe
        fields = [
            "titulo",
            "descricao",
            "responsavel",
            "prazo",
            "prioridade",
            "status",
            "checklist_texto",
            "comentarios",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "prazo": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "comentarios": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario_logado = usuario
        super().__init__(*args, **kwargs)
        self.fields["checklist_texto"].initial = "\n".join(getattr(self.instance, "checklist", []) or [])
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            self.fields["responsavel"].queryset = self.fields["responsavel"].queryset.filter(
                campanha_id=usuario.campanha_id
            )

    def clean_checklist_texto(self):
        return normalizar_checklist(self.cleaned_data.get("checklist_texto"))

    def clean(self):
        dados = super().clean()
        responsavel = dados.get("responsavel")
        campanha_id = getattr(self.usuario_logado, "campanha_id", None)
        if campanha_id and responsavel and responsavel.campanha_id != campanha_id:
            self.add_error("responsavel", "O responsavel precisa pertencer a mesma campanha.")
        return dados

    def save(self, commit=True):
        instancia = super().save(commit=False)
        instancia.checklist = self.cleaned_data.get("checklist_texto", [])
        if commit:
            instancia.save()
        return instancia
