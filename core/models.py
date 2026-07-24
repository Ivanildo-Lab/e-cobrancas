from django.db import models

class Empresa(models.Model):
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='banners/', blank=True, null=True)
    pix_chave = models.CharField(max_length=100, blank=True, null=True, verbose_name='Chave PIX')
    pix_titular = models.CharField(max_length=150, blank=True, null=True, verbose_name='Titular PIX')
    pix_banco = models.CharField(max_length=100, blank=True, null=True, verbose_name='Banco')
    pix_agencia = models.CharField(max_length=20, blank=True, null=True, verbose_name='Agencia')
    pix_conta = models.CharField(max_length=30, blank=True, null=True, verbose_name='Conta')
    pix_tipo_conta = models.CharField(max_length=20, blank=True, null=True, verbose_name='Tipo de Conta',
        choices=[('CC', 'Conta Corrente'), ('CP', 'Poupanca'), ('CI', 'Investimento')])
    assinatura = models.ImageField(upload_to='assinaturas/', blank=True, null=True, verbose_name='Imagem da Assinatura')
    responsavel = models.CharField(max_length=150, blank=True, null=True, verbose_name='Responsavel')

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nome

    @property
    def tem_dados_pagamento(self):
        return bool(self.pix_chave)


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
