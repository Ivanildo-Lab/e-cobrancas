from django.db import models
from django.utils import timezone


class Parcela(models.Model):
    cliente = models.ForeignKey('cadastros.Cliente', on_delete=models.CASCADE, related_name='parcelas', verbose_name='Cliente', db_column='cliente')
    parcela = models.CharField(max_length=30, db_column='parcela', verbose_name='Parcela')
    emissao = models.DateField(blank=True, null=True, db_column='emissao', verbose_name='Emissao')
    vencimento = models.DateField(db_index=True, db_column='vencimento', verbose_name='Vencimento')
    pagamento = models.DateField(blank=True, null=True, db_column='pagamento', verbose_name='Pagamento')
    valorconta = models.DecimalField(max_digits=10, decimal_places=2, db_column='valorconta', verbose_name='Valor (R$)')
    situacao = models.CharField(max_length=20, db_column='situacao', verbose_name='Situacao')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tbl_contasareceber'
        verbose_name = 'Parcela'
        verbose_name_plural = 'Parcelas'
        ordering = ['vencimento']

    def __str__(self):
        return f"{self.parcela} - {self.cliente.nome} - Venc: {self.vencimento} - {self.situacao}"

    @property
    def esta_vencida(self):
        return self.situacao.lower() == 'aberta' and self.vencimento < timezone.now().date()

    @property
    def status_cor(self):
        sit = (self.situacao or '').lower()
        if sit == 'liquidada':
            return 'green'
        elif sit in ('cancelada', 'cancelada'):
            return 'gray'
        elif self.esta_vencida:
            return 'red'
        return 'blue'

    @property
    def numero_parcela(self):
        return self.parcela

    @property
    def valor_parcela(self):
        return self.valorconta

    @property
    def data_vencimento(self):
        return self.vencimento

    @property
    def data_pagamento(self):
        return self.pagamento

    @property
    def status_texto(self):
        sit = (self.situacao or '').lower()
        if sit == 'aberta':
            return 'Atrasada' if self.esta_vencida else 'Aberta'
        return self.situacao

    @property
    def esta_vencida_display(self):
        return self.esta_vencida
