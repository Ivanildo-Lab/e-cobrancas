from django.contrib import admin
from .models import Parcela

@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = ['parcela', 'cliente', 'valorconta', 'vencimento', 'situacao']
    list_filter = ['situacao', 'vencimento']
    search_fields = ['parcela', 'cliente__nome']
    date_hierarchy = 'vencimento'
