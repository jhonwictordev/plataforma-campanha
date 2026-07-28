from calendar import monthrange
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import FiltroCampanhaMixin, MensagemSucessoMixin, NivelAcessoMixin
from core.permissions import PAPEIS_AGENDA_ESCRITA, PAPEIS_AGENDA_LEITURA, usuario_tem_nivel

from .forms import EventoAgendaFormulario
from .models import EventoAgenda
from .services import buscar_conflitos_evento

Usuario = get_user_model()


def _parse_data(valor: str | None, padrao: date) -> date:
    if not valor:
        return padrao
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return padrao


class AgendaQuerysetMixin:
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("responsavel")
            .prefetch_related("participantes", "liderancas_convidadas")
        )


class AgendaHomeView(LoginRequiredMixin, NivelAcessoMixin, FiltroCampanhaMixin, AgendaQuerysetMixin, ListView):
    model = EventoAgenda
    template_name = "agenda/lista.html"
    context_object_name = "eventos"
    niveis_permitidos = PAPEIS_AGENDA_LEITURA
    paginate_by = 20

    def _obter_visao(self) -> str:
        visao = self.request.GET.get("visao", "semana").strip().lower()
        if visao in {"dia", "semana", "mes"}:
            return visao
        return "semana"

    def _obter_referencia(self) -> date:
        return _parse_data(self.request.GET.get("referencia"), timezone.localdate())

    def _obter_periodo(self) -> tuple[date, date]:
        referencia = self._obter_referencia()
        visao = self._obter_visao()
        if visao == "dia":
            return referencia, referencia
        if visao == "mes":
            ultimo_dia = monthrange(referencia.year, referencia.month)[1]
            return referencia.replace(day=1), referencia.replace(day=ultimo_dia)
        inicio_semana = referencia - timedelta(days=referencia.weekday())
        return inicio_semana, inicio_semana + timedelta(days=6)

    def _obter_responsaveis(self):
        queryset = Usuario.objects.order_by("nome_completo", "pk")
        if not (self.request.user.is_superuser or self.request.user.is_staff):
            return queryset.filter(campanha_id=self.request.user.campanha_id)
        return queryset

    def _obter_ids_conflitantes(self, eventos):
        ids = set()
        for evento in eventos:
            conflitos = buscar_conflitos_evento(
                campanha=evento.campanha,
                data=evento.data,
                horario_inicial=evento.horario_inicial,
                horario_final=evento.horario_final,
                responsavel=evento.responsavel,
                participantes=evento.participantes.all(),
                liderancas=evento.liderancas_convidadas.all(),
                ignorar_evento_id=evento.pk,
            )
            if conflitos:
                ids.add(str(evento.pk))
        return ids

    def get_queryset(self):
        queryset = super().get_queryset()
        periodo_inicial, periodo_final = self._obter_periodo()
        busca = self.request.GET.get("busca", "").strip()
        tipo = self.request.GET.get("tipo", "").strip()
        status = self.request.GET.get("status", "").strip()
        responsavel = self.request.GET.get("responsavel", "").strip()

        queryset = queryset.filter(data__range=(periodo_inicial, periodo_final))
        if busca:
            queryset = queryset.filter(
                Q(titulo__icontains=busca) | Q(descricao__icontains=busca) | Q(endereco__icontains=busca)
            )
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if status:
            queryset = queryset.filter(status=status)
        if responsavel:
            queryset = queryset.filter(responsavel_id=responsavel)
        return queryset.order_by("data", "horario_inicial", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodo_inicial, periodo_final = self._obter_periodo()
        eventos_pagina = list(context["page_obj"].object_list if context.get("page_obj") else context["eventos"])
        hoje = timezone.localdate()
        object_list = self.object_list

        context["titulo"] = "Agenda compartilhada"
        context["descricao"] = "Organize compromissos, visitas e prazos da campanha com filtros por periodo e prevencao de conflitos."
        context["visao"] = self._obter_visao()
        context["referencia"] = self._obter_referencia().isoformat()
        context["periodo_inicial"] = periodo_inicial
        context["periodo_final"] = periodo_final
        context["tipo_opcoes"] = EventoAgenda.Tipos.choices
        context["status_opcoes"] = EventoAgenda.Status.choices
        context["responsaveis"] = self._obter_responsaveis()
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_AGENDA_ESCRITA)
        context["filtros"] = {
            "busca": self.request.GET.get("busca", ""),
            "tipo": self.request.GET.get("tipo", ""),
            "status": self.request.GET.get("status", ""),
            "responsavel": self.request.GET.get("responsavel", ""),
        }
        context["resumo"] = {
            "total": object_list.count(),
            "confirmados": object_list.filter(status=EventoAgenda.Status.CONFIRMADO).count(),
            "hoje": object_list.filter(data=hoje).count(),
            "pendentes": object_list.filter(data__lt=hoje).exclude(
                status__in=[EventoAgenda.Status.CONCLUIDO, EventoAgenda.Status.CANCELADO]
            ).count(),
        }
        context["eventos_com_conflito_ids"] = self._obter_ids_conflitantes(eventos_pagina)
        return context


class EventoAgendaCreateView(LoginRequiredMixin, NivelAcessoMixin, MensagemSucessoMixin, CreateView):
    model = EventoAgenda
    form_class = EventoAgendaFormulario
    template_name = "agenda/formulario.html"
    success_url = reverse_lazy("agenda:home")
    niveis_permitidos = PAPEIS_AGENDA_ESCRITA
    mensagem_sucesso = "Evento cadastrado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not getattr(self.request.user, "campanha", None):
            raise PermissionDenied("Vincule o usuario a uma campanha antes de cadastrar eventos.")
        form.instance.campanha = self.request.user.campanha
        return super().form_valid(form)


class EventoAgendaDetailView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    AgendaQuerysetMixin,
    DetailView,
):
    model = EventoAgenda
    template_name = "agenda/detalhe.html"
    context_object_name = "evento"
    niveis_permitidos = PAPEIS_AGENDA_LEITURA

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = self.object
        context["pode_editar"] = usuario_tem_nivel(self.request.user, PAPEIS_AGENDA_ESCRITA)
        context["eventos_conflitantes"] = buscar_conflitos_evento(
            campanha=evento.campanha,
            data=evento.data,
            horario_inicial=evento.horario_inicial,
            horario_final=evento.horario_final,
            responsavel=evento.responsavel,
            participantes=evento.participantes.all(),
            liderancas=evento.liderancas_convidadas.all(),
            ignorar_evento_id=evento.pk,
        )
        return context


class EventoAgendaUpdateView(
    LoginRequiredMixin,
    NivelAcessoMixin,
    FiltroCampanhaMixin,
    AgendaQuerysetMixin,
    MensagemSucessoMixin,
    UpdateView,
):
    model = EventoAgenda
    form_class = EventoAgendaFormulario
    template_name = "agenda/formulario.html"
    success_url = reverse_lazy("agenda:home")
    niveis_permitidos = PAPEIS_AGENDA_ESCRITA
    mensagem_sucesso = "Evento atualizado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs
