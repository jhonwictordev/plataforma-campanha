from django.contrib import admin

from .models import CategoriaFinanceira, CentroCusto, LancamentoFinanceiro, ParceiroFinanceiro


admin.site.register(CategoriaFinanceira)
admin.site.register(CentroCusto)
admin.site.register(ParceiroFinanceiro)
admin.site.register(LancamentoFinanceiro)
