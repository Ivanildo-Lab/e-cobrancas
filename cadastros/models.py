from django.db import models


class Cidade(models.Model):
    nome = models.CharField(max_length=100, db_column='nome', verbose_name='Nome da Cidade')
    uf = models.CharField(max_length=2, db_column='uf', verbose_name='Estado (UF)')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tbl_cidades'
        verbose_name = 'Cidade'
        verbose_name_plural = 'Cidades'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome}/{self.uf}"


class Cliente(models.Model):
    nome = models.CharField(max_length=150, verbose_name='Nome Completo')
    contato = models.CharField(max_length=150, blank=True, null=True, verbose_name='Pessoa de Contato')
    cidade = models.ForeignKey(Cidade, on_delete=models.PROTECT, related_name='clientes', verbose_name='Cidade', db_column='cidade')
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Telefone/Celular')
    diacobranca = models.SmallIntegerField(blank=True, null=True, verbose_name='Dia Cobranca')
    valormensalidade = models.FloatField(blank=True, null=True, verbose_name='Valor Mensalidade')
    obs = models.TextField(blank=True, null=True, verbose_name='Observacoes')
    conexao = models.CharField(max_length=100, blank=True, null=True, verbose_name='Conexao/Relacionamento')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tbl_clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']

    def __str__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f"{self.nome} ({status})"

    @property
    def telefone_formatado(self):
        if not self.telefone:
            return ''
        return ''.join(filter(str.isdigit, self.telefone))
