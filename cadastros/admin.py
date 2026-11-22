from django.contrib import admin
from .models import Cidade, Cliente, ClienteTelegram

@admin.register(Cidade)
class CidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'uf']
    list_filter = ['uf']

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'razao_social', 'cpf', 'cnpj', 'telefone', 'contato', 'cidade', 'ativo']
    list_filter = ['ativo', 'cidade']
    search_fields = ['nome', 'razao_social', 'cpf', 'cnpj', 'contato']

@admin.register(ClienteTelegram)
class ClienteTelegramAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'chat_id', 'primeiro_nome', 'ativo', 'criado_em']
    list_filter = ['ativo']
    search_fields = ['cliente__nome', 'chat_id', 'primeiro_nome']
    readonly_fields = ['criado_em', 'atualizado_em']
