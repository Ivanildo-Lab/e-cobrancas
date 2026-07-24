from django.db import models

class Empresa(models.Model):
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='banners/', blank=True, null=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nome


class ModeloSaaS(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='%(class)s_set')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ParametroSistema(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='parametros')
    chave = models.CharField(max_length=100)
    valor = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Parametro do Sistema'
        unique_together = ['empresa', 'chave']

    def __str__(self):
        return f"{self.chave}: {self.valor}"
