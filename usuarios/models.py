from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    telefone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.get_full_name() or self.username
