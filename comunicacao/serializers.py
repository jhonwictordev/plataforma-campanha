from django.utils import timezone
from rest_framework import serializers

from eleitores.models import ContatoCRM

from .models import CampanhaComunicacao, EnvioComunicacao, ListaBloqueio, ModeloMensagem, NotificacaoInterna
from .services import analisar_destinatarios, registrar_descadastro, sincronizar_envios_campanha


class ModeloMensagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeloMensagem
        fields = ["id", "campanha", "nome", "assunto", "conteudo", "canal", "criado_em", "atualizado_em"]
        read_only_fields = ("id", "criado_em", "atualizado_em")
        extra_kwargs = {"campanha": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        usuario = self.context["request"].user
        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})
        return attrs


class ListaBloqueioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListaBloqueio
        fields = [
            "id",
            "campanha",
            "contato",
            "canal",
            "motivo",
            "solicitado_por",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")
        extra_kwargs = {"campanha": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        usuario = self.context["request"].user
        contato = attrs.get("contato", getattr(self.instance, "contato", None))
        canal = attrs.get("canal", getattr(self.instance, "canal", None))

        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
            attrs.setdefault("solicitado_por", usuario)
            if contato and contato.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError({"contato": "O contato precisa pertencer a mesma campanha."})
            queryset = ListaBloqueio.objects.filter(campanha=usuario.campanha, contato=contato, canal=canal)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if contato and canal and queryset.exists():
                raise serializers.ValidationError({"contato": "Ja existe um bloqueio ativo para este contato e canal."})
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})
        return attrs


class CampanhaComunicacaoSerializer(serializers.ModelSerializer):
    destinatarios = serializers.PrimaryKeyRelatedField(
        queryset=ContatoCRM.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = CampanhaComunicacao
        fields = [
            "id",
            "campanha",
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
            "quantidade_programada",
            "quantidade_enviada",
            "quantidade_entregue",
            "quantidade_falha",
            "quantidade_respostas",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = (
            "id",
            "quantidade_programada",
            "quantidade_enviada",
            "quantidade_entregue",
            "quantidade_falha",
            "quantidade_respostas",
            "criado_em",
            "atualizado_em",
        )
        extra_kwargs = {
            "campanha": {"required": False, "allow_null": True},
            "assunto": {"required": False, "allow_blank": True},
            "conteudo": {"required": False, "allow_blank": True},
            "responsavel": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        usuario = self.context["request"].user
        modelo = attrs.get("modelo_mensagem", getattr(self.instance, "modelo_mensagem", None))
        responsavel = attrs.get("responsavel", getattr(self.instance, "responsavel", None))
        canal = attrs.get("canal", getattr(self.instance, "canal", None))
        destinatarios = attrs.get("destinatarios")
        status = attrs.get("status", getattr(self.instance, "status", None))
        data_envio = attrs.get("data_envio", getattr(self.instance, "data_envio", None))

        if modelo and not attrs.get("assunto") and not getattr(self.instance, "assunto", "") and modelo.assunto:
            attrs["assunto"] = modelo.assunto
        if modelo and not attrs.get("conteudo") and not getattr(self.instance, "conteudo", ""):
            attrs["conteudo"] = modelo.conteudo
        if not attrs.get("conteudo") and not getattr(self.instance, "conteudo", ""):
            raise serializers.ValidationError({"conteudo": "Informe o conteudo da comunicacao."})
        if status == CampanhaComunicacao.Status.AGENDADA and not data_envio:
            raise serializers.ValidationError({"data_envio": "Informe a data e hora para agendar a comunicacao."})
        if status == CampanhaComunicacao.Status.AGENDADA:
            destinatarios_atuais = destinatarios
            if destinatarios_atuais is None and self.instance:
                destinatarios_atuais = self.instance.destinatarios.all()
            if not destinatarios_atuais:
                raise serializers.ValidationError(
                    {"destinatarios": "Selecione ao menos um destinatario para agendar a campanha."}
                )

        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
            attrs.setdefault("responsavel", usuario)
            if modelo and modelo.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError({"modelo_mensagem": "O modelo precisa pertencer a mesma campanha."})
            if responsavel and responsavel.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError({"responsavel": "O responsavel precisa pertencer a mesma campanha."})
            if destinatarios is not None and canal:
                erros = analisar_destinatarios(
                    campanha_id=usuario.campanha_id,
                    canal=canal,
                    destinatarios=destinatarios,
                )
                if erros.get("outra_campanha"):
                    raise serializers.ValidationError({"destinatarios": "Existem destinatarios vinculados a outra campanha."})
                if erros.get("sem_consentimento"):
                    raise serializers.ValidationError({"destinatarios": "Existem destinatarios sem consentimento valido."})
                if erros.get("canal_nao_autorizado"):
                    raise serializers.ValidationError(
                        {"destinatarios": "Existem destinatarios sem autorizacao para o canal selecionado."}
                    )
                if erros.get("bloqueados"):
                    raise serializers.ValidationError({"destinatarios": "Existem destinatarios bloqueados para este canal."})
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})

        return attrs

    def create(self, validated_data):
        destinatarios = validated_data.pop("destinatarios", [])
        usuario = self.context["request"].user
        instancia = super().create(validated_data)
        instancia.destinatarios.set(destinatarios)
        sincronizar_envios_campanha(instancia, destinatarios, usuario=usuario)
        return instancia

    def update(self, instance, validated_data):
        destinatarios = validated_data.pop("destinatarios", None)
        usuario = self.context["request"].user
        instancia = super().update(instance, validated_data)
        if destinatarios is not None:
            instancia.destinatarios.set(destinatarios)
        else:
            destinatarios = instancia.destinatarios.all()
        sincronizar_envios_campanha(instancia, destinatarios, usuario=usuario)
        return instancia


class EnvioComunicacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvioComunicacao
        fields = [
            "id",
            "campanha",
            "campanha_comunicacao",
            "contato",
            "canal",
            "status",
            "mensagem_enviada",
            "erro_envio",
            "resposta_recebida",
            "data_programada",
            "data_envio",
            "data_entrega",
            "data_resposta",
            "cancelou_inscricao",
            "observacoes_internas",
            "responsavel_registro",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")
        extra_kwargs = {"campanha": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        usuario = self.context["request"].user
        campanha_comunicacao = attrs.get("campanha_comunicacao", getattr(self.instance, "campanha_comunicacao", None))
        contato = attrs.get("contato", getattr(self.instance, "contato", None))
        canal = attrs.get("canal", getattr(self.instance, "canal", None))
        status = attrs.get("status", getattr(self.instance, "status", None))

        if campanha_comunicacao and not canal:
            attrs["canal"] = campanha_comunicacao.canal
            canal = campanha_comunicacao.canal
        if campanha_comunicacao and contato and contato.campanha_id != campanha_comunicacao.campanha_id:
            raise serializers.ValidationError({"contato": "O contato precisa pertencer a mesma campanha da comunicacao."})
        if status == EnvioComunicacao.Status.FALHA and not attrs.get("erro_envio", getattr(self.instance, "erro_envio", "")):
            raise serializers.ValidationError({"erro_envio": "Informe a falha registrada para este envio."})
        if status == EnvioComunicacao.Status.RESPONDIDO and not attrs.get(
            "resposta_recebida", getattr(self.instance, "resposta_recebida", "")
        ):
            raise serializers.ValidationError({"resposta_recebida": "Informe a resposta recebida do destinatario."})

        if not (usuario.is_superuser or usuario.is_staff):
            attrs["campanha"] = usuario.campanha
            attrs.setdefault("responsavel_registro", usuario)
            if campanha_comunicacao and campanha_comunicacao.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError(
                    {"campanha_comunicacao": "A campanha de comunicacao precisa pertencer a mesma campanha."}
                )
            if contato and contato.campanha_id != usuario.campanha_id:
                raise serializers.ValidationError({"contato": "O contato precisa pertencer a mesma campanha."})
            if campanha_comunicacao and canal and campanha_comunicacao.canal != canal:
                raise serializers.ValidationError({"canal": "O canal do envio precisa ser o mesmo da campanha de comunicacao."})
        elif not attrs.get("campanha") and not getattr(self.instance, "campanha", None):
            raise serializers.ValidationError({"campanha": "Informe a campanha do registro."})

        return attrs

    def create(self, validated_data):
        instancia = super().create(validated_data)
        registrar_descadastro(instancia, usuario=self.context["request"].user)
        instancia.campanha_comunicacao.atualizar_metricas()
        return instancia

    def update(self, instance, validated_data):
        instancia = super().update(instance, validated_data)
        registrar_descadastro(instancia, usuario=self.context["request"].user)
        instancia.campanha_comunicacao.atualizar_metricas()
        return instancia


class NotificacaoInternaSerializer(serializers.ModelSerializer):
    foi_lida = serializers.BooleanField(read_only=True)

    class Meta:
        model = NotificacaoInterna
        fields = [
            "id",
            "campanha",
            "usuario_destinatario",
            "titulo",
            "mensagem",
            "categoria",
            "url_destino",
            "origem_modelo",
            "origem_id",
            "enviada_em",
            "lida_em",
            "foi_lida",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = (
            "id",
            "campanha",
            "usuario_destinatario",
            "titulo",
            "mensagem",
            "categoria",
            "url_destino",
            "origem_modelo",
            "origem_id",
            "enviada_em",
            "criado_em",
            "atualizado_em",
        )

    def validate(self, attrs):
        if "lida_em" in attrs and attrs["lida_em"] is None:
            attrs["lida_em"] = timezone.now()
        return attrs
