from django import forms
from django.core.exceptions import ValidationError

from core.forms import FormularioBootstrapMixin

from .models import EventoAgenda
from .services import buscar_conflitos_evento, descrever_evento, normalizar_checklist


class EventoAgendaFormulario(FormularioBootstrapMixin):
    checklist_texto = forms.CharField(
        label="Checklist",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Informe um item por linha para acompanhar a execuÃ§Ã£o do evento.",
    )

    class Meta:
        model = EventoAgenda
        fields = [
            "titulo",
            "descricao",
            "tipo",
            "data",
            "horario_inicial",
            "horario_final",
            "endereco",
            "link_localizacao",
            "responsavel",
            "participantes",
            "liderancas_convidadas",
            "status",
            "prioridade",
            "checklist_texto",
            "observacoes",
            "latitude",
            "longitude",
        ]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "horario_inicial": forms.TimeInput(attrs={"type": "time"}),
            "horario_final": forms.TimeInput(attrs={"type": "time"}),
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "participantes": forms.SelectMultiple(attrs={"size": 6}),
            "liderancas_convidadas": forms.SelectMultiple(attrs={"size": 6}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        self.fields["checklist_texto"].initial = "\n".join(getattr(self.instance, "checklist", []) or [])
        if usuario and getattr(usuario, "campanha_id", None) and not (usuario.is_superuser or usuario.is_staff):
            campanha_id = usuario.campanha_id
            self.fields["responsavel"].queryset = self.fields["responsavel"].queryset.filter(campanha_id=campanha_id)
            self.fields["participantes"].queryset = self.fields["participantes"].queryset.filter(campanha_id=campanha_id)
            self.fields["liderancas_convidadas"].queryset = self.fields["liderancas_convidadas"].queryset.filter(
                campanha_id=campanha_id
            )
            if not self.instance.pk:
                self.fields["responsavel"].initial = usuario.pk

    def clean_checklist_texto(self):
        return normalizar_checklist(self.cleaned_data.get("checklist_texto"))

    def clean(self):
        dados = super().clean()
        horario_inicial = dados.get("horario_inicial")
        horario_final = dados.get("horario_final")
        if horario_inicial and horario_final and horario_final < horario_inicial:
            self.add_error("horario_final", "O horÃ¡rio final deve ser igual ou posterior ao horÃ¡rio inicial.")

        campanha = getattr(self.usuario, "campanha", None) or getattr(self.instance, "campanha", None)
        data = dados.get("data")
        responsavel = dados.get("responsavel") or self.usuario or getattr(self.instance, "responsavel", None)
        participantes = list(dados.get("participantes") or [])
        liderancas = list(dados.get("liderancas_convidadas") or [])
        if campanha and data and horario_inicial:
            conflitos = buscar_conflitos_evento(
                campanha=campanha,
                data=data,
                horario_inicial=horario_inicial,
                horario_final=horario_final,
                responsavel=responsavel,
                participantes=participantes,
                liderancas=liderancas,
                ignorar_evento_id=self.instance.pk,
            )
            if conflitos:
                resumo = "; ".join(descrever_evento(evento) for evento in conflitos[:3])
                raise ValidationError(
                    f"Existe conflito de agenda com os seguintes eventos: {resumo}."
                )
            dados["eventos_conflitantes"] = conflitos
        return dados

    def save(self, commit=True):
        instancia = super().save(commit=False)
        instancia.checklist = self.cleaned_data.get("checklist_texto", [])
        if self.usuario and not instancia.responsavel_id:
            instancia.responsavel = self.usuario
        if commit:
            instancia.save()
            self.save_m2m()
        return instancia
