from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'empresa', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Dados Extras', {'fields': ('empresa', 'telefone')}),
    )
