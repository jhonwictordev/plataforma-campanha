from rest_framework import serializers

from .models import ComentarioTarefaEquipe, IntegranteEquipe, TarefaEquipe


class IntegranteEquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegranteEquipe
        fields = [
            "id",
            "campanha",
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
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        responsavel_direto = attrs.get("responsavel_direto")
        usuario = attrs.get("usuario")

        if self.instance and responsavel_direto and responsavel_direto.pk == self.instance.pk:
            raise serializers.ValidationError(
                {"responsavel_direto": "O integrante nao pode ser responsavel direto de si mesmo."}
            )

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            if responsavel_direto and responsavel_direto.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel_direto": "O responsavel direto precisa pertencer a mesma campanha."}
                )
            if usuario and usuario.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"usuario": "O usuario vinculado precisa pertencer a mesma campanha."}
                )

        return attrs


class TarefaEquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TarefaEquipe
        fields = [
            "id",
            "campanha",
            "titulo",
            "descricao",
            "responsavel",
            "prazo",
            "prioridade",
            "status",
            "checklist",
            "comentarios",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        responsavel = attrs.get("responsavel")

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            if responsavel and responsavel.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"responsavel": "O responsavel precisa pertencer a mesma campanha."}
                )

        return attrs


class ComentarioTarefaEquipeSerializer(serializers.ModelSerializer):
    autor_nome = serializers.CharField(source="autor.nome_completo", read_only=True)

    class Meta:
        model = ComentarioTarefaEquipe
        fields = [
            "id",
            "campanha",
            "tarefa",
            "autor",
            "autor_nome",
            "conteudo",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ("id", "autor", "autor_nome", "criado_em", "atualizado_em")

    def validate(self, attrs):
        usuario_logado = self.context["request"].user
        tarefa = attrs.get("tarefa") or getattr(self.instance, "tarefa", None)
        campanha = attrs.get("campanha") or getattr(self.instance, "campanha", None)

        if tarefa and campanha and tarefa.campanha_id != getattr(campanha, "id", campanha):
            raise serializers.ValidationError(
                {"tarefa": "A tarefa informada precisa pertencer a mesma campanha do comentario."}
            )

        if not (usuario_logado.is_superuser or usuario_logado.is_staff):
            attrs["campanha"] = usuario_logado.campanha
            if tarefa and tarefa.campanha_id != usuario_logado.campanha_id:
                raise serializers.ValidationError(
                    {"tarefa": "A tarefa precisa pertencer a mesma campanha do usuario autenticado."}
                )

        return attrs

    def create(self, validated_data):
        validated_data.setdefault("autor", self.context["request"].user)
        validated_data["campanha"] = validated_data["tarefa"].campanha
        return super().create(validated_data)
