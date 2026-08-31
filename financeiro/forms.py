from django import forms
from .models import Parcela
from cadastros.models import Cliente, Cidade

INPUT_CLASSES = 'w-full border border-gray-300 rounded p-2 text-sm shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
SELECT_CLASSES = 'w-full border border-gray-300 rounded p-2 text-sm shadow-sm focus:ring-2 focus:ring-blue-500'


class GerarParcelasForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True).order_by('nome'),
        label='Selecione o Cliente',
        widget=forms.Select(attrs={'class': SELECT_CLASSES}),
        empty_label='-- Selecione um cliente --',
    )
    valor_parcela = forms.DecimalField(
        max_digits=10, decimal_places=2,
        label='Valor de Cada Parcela (R$)',
        required=False,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES, 'step': '0.01', 'min': '0', 'id': 'id_valor_parcela'}),
    )
    valor_divida = forms.DecimalField(
        max_digits=12, decimal_places=2,
        label='Valor Total da Divida (R$)',
        required=False,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES, 'step': '0.01', 'min': '0', 'id': 'id_valor_divida'}),
    )
    percentual_juros = forms.DecimalField(
        max_digits=5, decimal_places=2,
        label='Percentual de Juros (%)',
        required=False,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES, 'step': '0.01', 'min': '0', 'id': 'id_percentual_juros'}),
    )
    quantidade_parcelas = forms.IntegerField(
        label='Quantidade de Parcelas',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': '1'}),
    )
    primeiro_vencimento = forms.DateField(
        label='Data do Primeiro Vencimento',
        widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
    )
    periodicidade = forms.ChoiceField(
        choices=[('mensal', 'Mensal')],
        label='Periodicidade',
        widget=forms.Select(attrs={'class': SELECT_CLASSES}),
    )

    def clean(self):
        cleaned_data = super().clean()
        valor_parcela = cleaned_data.get('valor_parcela')
        valor_divida = cleaned_data.get('valor_divida')
        if not valor_parcela and not valor_divida:
            raise forms.ValidationError('Informe o Valor da Parcela OU o Valor Total da Divida.')
        if valor_parcela and valor_divida:
            raise forms.ValidationError('Informe apenas UM dos campos: Valor da Parcela ou Valor Total da Divida.')
        return cleaned_data


class EditarParcelaForm(forms.ModelForm):
    class Meta:
        model = Parcela
        fields = ['valorconta', 'vencimento']
        widgets = {
            'valorconta': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'step': '0.01'}),
            'vencimento': forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}, format='%Y-%m-%d'),
        }


class RegistrarPagamentoForm(forms.Form):
    data_pagamento = forms.DateField(
        label='Data do Pagamento',
        widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
    )


class BaixaLoteForm(forms.Form):
    data_pagamento = forms.DateField(
        label='Data do Pagamento',
        widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
    )


class FiltroParcelasForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ('aberta', 'Abertas (Nao Vencidas)'),
            ('todas', 'Todas'),
            ('atrasada', 'Atrasadas'),
            ('liquidada', 'Liquidadas'),
            ('cancelada', 'Canceladas'),
        ],
        required=False,
        initial='aberta',
        widget=forms.Select(attrs={'class': SELECT_CLASSES}),
    )
    cliente = forms.CharField(
        required=False,
        label='Cliente',
        widget=forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Nome, Razão, CPF ou CNPJ...', 'list': 'clientes-list'}),
    )
    venc_inicio = forms.DateField(
        required=False,
        label='Vencimento (Inicio)',
        widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
    )
    venc_fim = forms.DateField(
        required=False,
        label='Vencimento (Fim)',
        widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
    )
    pag_inicio = forms.DateField(
        required=False,
        label='Pagamento (Inicio)',
        widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
    )
    pag_fim = forms.DateField(
        required=False,
        label='Pagamento (Fim)',
        widget=forms.DateInput(attrs={'class': INPUT_CLASSES, 'type': 'date'}),
    )


class FiltroClientesForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Buscar por nome ou contato...'}),
    )
    status = forms.ChoiceField(
        choices=[
            ('ativos', 'Ativos'),
            ('inativos', 'Inativos'),
            ('todos', 'Todos'),
        ],
        required=False,
        initial='ativos',
        widget=forms.Select(attrs={'class': SELECT_CLASSES}),
    )
    cidade = forms.ModelChoiceField(
        queryset=Cidade.objects.all().order_by('nome'),
        required=False,
        label='Cidade',
        empty_label='-- Todas as Cidades --',
        widget=forms.Select(attrs={'class': SELECT_CLASSES}),
    )
