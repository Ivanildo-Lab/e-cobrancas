from django.contrib import admin
from .models import Cidade, Cliente

@admin.register(Cidade)
class CidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'uf']
    list_filter = ['uf']

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'telefone', 'contato', 'cidade', 'ativo']
    list_filter = ['ativo', 'cidade']
    search_fields = ['nome', 'contato']
