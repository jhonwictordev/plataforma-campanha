from rest_framework import serializers

from .models import EventoAgenda
from .services import buscar_conflitos_evento, descrever_evento


class EventoAgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoAgenda
        fields = [
            "id",
            "campanha",
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
            "checklist",
            "observacoes",
            "latitude",
            "longitude",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario = self.context["request"].user
        campanha = attrs.get("campanha") or getattr(self.instance, "campanha", None) or getattr(usuario, "campanha", None)
        horario_inicial = attrs.get("horario_inicial") or getattr(self.instance, "horario_inicial", None)
        horario_final = (
            attrs.get("horario_final")
            if "horario_final" in attrs
            else getattr(self.instance, "horario_final", None)
        )
        data = attrs.get("data") or getattr(self.instance, "data", None)
        responsavel = attrs.get("responsavel") or getattr(self.instance, "responsavel", None) or usuario

        if horario_inicial and horario_final and horario_final < horario_inicial:
            raise serializers.ValidationError(
                {"horario_final": "O horário final deve ser igual ou posterior ao horário inicial."}
            )

        participantes = attrs.get("participantes")
        if participantes is None and self.instance is not None:
            participantes = list(self.instance.participantes.all())
        else:
            participantes = list(participantes or [])

        liderancas = attrs.get("liderancas_convidadas")
        if liderancas is None and self.instance is not None:
            liderancas = list(self.instance.liderancas_convidadas.all())
        else:
            liderancas = list(liderancas or [])

        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
            if responsavel and responsavel.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel": "O responsável precisa pertencer à mesma campanha."}
                )
            if any(participante.campanha_id != usuario.campanha_id for participante in participantes):
                raise serializers.ValidationError(
                    {"participantes": "Todos os participantes precisam pertencer à mesma campanha."}
                )
            if any(lideranca.campanha_id != usuario.campanha_id for lideranca in liderancas):
                raise serializers.ValidationError(
                    {"liderancas_convidadas": "As lideranças convidadas precisam pertencer à mesma campanha."}
                )
            attrs.setdefault("responsavel", responsavel or usuario)

        if campanha and data and horario_inicial:
            conflitos = buscar_conflitos_evento(
                campanha=campanha,
                data=data,
                horario_inicial=horario_inicial,
                horario_final=horario_final,
                responsavel=responsavel,
                participantes=participantes,
                liderancas=liderancas,
                ignorar_evento_id=getattr(self.instance, "pk", None),
            )
            if conflitos:
                resumo = "; ".join(descrever_evento(evento) for evento in conflitos[:3])
                raise serializers.ValidationError(
                    {"non_field_errors": [f"Existe conflito de agenda com os seguintes eventos: {resumo}."]}
                )

        return attrs
