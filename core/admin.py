from django.contrib import admin
from .models import Empresa, ParametroSistema

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj']

@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ['chave', 'valor', 'empresa']
