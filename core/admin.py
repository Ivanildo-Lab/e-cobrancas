from django.contrib import admin
from .models import Empresa, ParametroSistema

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj', 'pix_chave', 'pix_banco']
    fieldsets = [
        ('Dados da Empresa', {'fields': ['nome', 'cnpj', 'logo', 'banner']}),
        ('Dados para Pagamento', {'fields': [
            'pix_chave', 'pix_titular', 'pix_banco', 'pix_agencia',
            'pix_conta', 'pix_tipo_conta'
        ]}),
        ('Assinatura', {'fields': ['assinatura', 'responsavel']}),
    ]

@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ['chave', 'valor', 'empresa']
