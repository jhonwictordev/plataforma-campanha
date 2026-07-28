from rest_framework import serializers


class MapaEleitoralRespostaSerializer(serializers.Serializer):
    camada = serializers.CharField()
    periodo = serializers.CharField()
    data_inicial = serializers.DateField()
    data_final = serializers.DateField()
    filtros = serializers.JSONField()
    visibilidade = serializers.JSONField()
    camadas = serializers.JSONField()
    resumo = serializers.JSONField()
    destaques = serializers.JSONField()
