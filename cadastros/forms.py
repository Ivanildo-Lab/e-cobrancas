from django import forms
from .models import Cidade, Cliente

ESTADOS_BRASILEIROS = [
    ('', '---------'),
    ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'), ('BA', 'BA'),
    ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'), ('GO', 'GO'), ('MA', 'MA'),
    ('MT', 'MT'), ('MS', 'MS'), ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'),
    ('PR', 'PR'), ('PE', 'PE'), ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'),
    ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), ('SC', 'SC'), ('SP', 'SP'),
    ('SE', 'SE'), ('TO', 'TO'),
]

INPUT_CLASSES = 'w-full border border-gray-300 rounded p-2 text-sm shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
SELECT_CLASSES = 'w-full border border-gray-300 rounded p-2 text-sm shadow-sm focus:ring-2 focus:ring-blue-500'


class CidadeForm(forms.ModelForm):
    class Meta:
        model = Cidade
        fields = ['nome', 'uf']
        widgets = {
            'nome': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Nome da cidade'}),
            'uf': forms.Select(attrs={'class': SELECT_CLASSES}, choices=ESTADOS_BRASILEIROS),
        }


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nome', 'contato', 'conexao', 'cidade', 'telefone',
            'valormensalidade', 'diacobranca', 'obs', 'ativo',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Nome completo do cliente'}),
            'contato': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Pessoa de contato'}),
            'conexao': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Indicacao, site, etc.'}),
            'cidade': forms.Select(attrs={'class': SELECT_CLASSES}),
            'telefone': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': '(00) 00000-0000'}),
            'valormensalidade': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'step': '0.01', 'min': '0'}),
            'diacobranca': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': '1', 'max': '31'}),
            'obs': forms.Textarea(attrs={'class': INPUT_CLASSES, 'rows': 3, 'placeholder': 'Observacoes'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'w-5 h-5 accent-blue-600 cursor-pointer'}),
        }
