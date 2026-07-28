from rest_framework import serializers

from .models import LogSeguranca, PoliticaRetencaoDados, RegistroAuditoria, SolicitacaoTitularDados


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = RegistroAuditoria
        fields = [
            "id",
            "campanha",
            "acao",
            "modelo",
            "objeto_id",
            "resumo",
            "dados_anteriores",
            "dados_novos",
            "usuario",
            "usuario_nome",
            "endereco_ip",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = fields


class LogSegurancaSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = LogSeguranca
        fields = [
            "id",
            "campanha",
            "evento",
            "severidade",
            "descricao",
            "usuario",
            "usuario_nome",
            "endereco_ip",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = fields


class PoliticaRetencaoDadosSerializer(serializers.ModelSerializer):
    responsavel_nome = serializers.CharField(source="responsavel.nome_completo", read_only=True)

    class Meta:
        model = PoliticaRetencaoDados
        fields = [
            "id",
            "campanha",
            "nome",
            "tipo_registro",
            "base_legal",
            "dias_retencao",
            "dias_ate_anonimizacao",
            "anonimizar_ao_expirar",
            "observacoes",
            "responsavel",
            "responsavel_nome",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "responsavel_nome", "criado_em", "atualizado_em")
        extra_kwargs = {
            "campanha": {"required": False},
        }

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        campanha = attrs.get("campanha") or getattr(self.instance, "campanha", None)
        responsavel = attrs.get("responsavel") or getattr(self.instance, "responsavel", None)

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            campanha = usuario_logado.campanha

        if campanha and responsavel and responsavel.campanha_id != campanha.id:
            raise serializers.ValidationError(
                {"responsavel": "O responsavel informado precisa pertencer a mesma campanha da politica."}
            )

        return attrs


class SolicitacaoTitularDadosSerializer(serializers.ModelSerializer):
    responsavel_interno_nome = serializers.CharField(source="responsavel_interno.nome_completo", read_only=True)
    executar_acao_lgpd = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = SolicitacaoTitularDados
        fields = [
            "id",
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
            "responsavel_interno_nome",
            "prazo_resposta",
            "resposta_interna",
            "executar_acao_lgpd",
            "executado_em",
            "resultado_execucao",
            "data_conclusao",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = (
            "id",
            "responsavel_interno_nome",
            "executado_em",
            "resultado_execucao",
            "data_conclusao",
            "criado_em",
            "atualizado_em",
        )
        extra_kwargs = {
            "campanha": {"required": False},
        }

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        campanha = attrs.get("campanha") or getattr(self.instance, "campanha", None)
        contato = attrs.get("contato_relacionado") or getattr(self.instance, "contato_relacionado", None)
        lideranca = attrs.get("lideranca_relacionada") or getattr(self.instance, "lideranca_relacionada", None)
        responsavel_interno = attrs.get("responsavel_interno") or getattr(self.instance, "responsavel_interno", None)
        executar_acao = attrs.get("executar_acao_lgpd", False)

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            campanha = usuario_logado.campanha

        if campanha and contato and contato.campanha_id != campanha.id:
            raise serializers.ValidationError(
                {"contato_relacionado": "O contato informado precisa pertencer a mesma campanha da solicitacao."}
            )
        if campanha and lideranca and lideranca.campanha_id != campanha.id:
            raise serializers.ValidationError(
                {"lideranca_relacionada": "A lideranca informada precisa pertencer a mesma campanha da solicitacao."}
            )
        if campanha and responsavel_interno and responsavel_interno.campanha_id != campanha.id:
            raise serializers.ValidationError(
                {"responsavel_interno": "O responsavel interno precisa pertencer a mesma campanha da solicitacao."}
            )
        if executar_acao and not contato and not lideranca:
            raise serializers.ValidationError(
                {"executar_acao_lgpd": "Vincule um contato ou lideranca antes de executar a acao automatica."}
            )

        return attrs
