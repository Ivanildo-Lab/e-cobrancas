"""
Management command para importar dados do Supabase para o Django.
Uso: python manage.py importar_supabase

Mapeamento de tabelas Supabase -> Django:
  Supabase "clientes" -> cadastros.Cliente
  Supabase "parcelas" / "contas" -> financeiro.Parcela
  Supabase "cidades" -> cadastros.Cidade

Ajuste os nomes das tabelas e colunas conforme o schema real do seu Supabase.
"""
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from cadastros.models import Cidade, Cliente
from financeiro.models import Parcela, StatusParcela
from core.models import Empresa


class Command(BaseCommand):
    help = 'Importa dados do Supabase para o banco Django'

    def add_arguments(self, parser):
        parser.add_argument('--tabela', type=str, help='Tabela especifica para importar (cidades, clientes, parcelas, todas)')
        parser.add_argument('--empresa-id', type=int, default=1, help='ID da empresa para vincular os dados')
        parser.add_argument('--supabase-url', type=str, default='', help='URL do Supabase (override)')
        parser.add_argument('--supabase-key', type=str, default='', help='Service key do Supabase (override)')

    def _get_headers(self):
        key = self._service_key or settings.SUPABASE_SERVICE_KEY
        return {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
        }

    def _query_table(self, table_name, select='*', limit=1000, offset=0):
        url = f'{self._base_url}/rest/v1/{table_name}?select={select}&limit={limit}&offset={offset}'
        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                self.stdout.write(self.style.WARNING(f'Tabela "{table_name}" nao encontrada no Supabase.'))
                return None
            else:
                self.stdout.write(self.style.ERROR(f'Erro ao consultar {table_name}: {resp.status_code} - {resp.text[:200]}'))
                return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro de conexao ao consultar {table_name}: {e}'))
            return None

    def _importar_cidades(self, empresa):
        self.stdout.write('Importando cidades...')
        dados = self._query_table('cidades')
        if dados is None:
            self.stdout.write(self.style.WARNING('Tabela "cidades" nao encontrada. Tentando "cidade"...'))
            dados = self._query_table('cidade')
        if dados is None:
            self.stdout.write(self.style.WARNING('Nenhuma tabela de cidades encontrada. Pulando.'))
            return 0

        count = 0
        for item in dados:
            nome = item.get('nome_cidade') or item.get('nome') or item.get('name', '')
            estado = item.get('estado') or item.get('uf') or item.get('state', '')
            if nome:
                _, created = Cidade.objects.get_or_create(
                    nome_cidade=nome,
                    estado=estado[:2] if estado else '',
                    empresa=empresa,
                )
                if created:
                    count += 1
        self.stdout.write(self.style.SUCCESS(f'  {count} cidades importadas.'))
        return count

    def _importar_clientes(self, empresa):
        self.stdout.write('Importando clientes...')
        dados = self._query_table('clientes')
        if dados is None:
            self.stdout.write(self.style.WARNING('Tabela "clientes" nao encontrada. Tentando "cliente"...'))
            dados = self._query_table('cliente')
        if dados is None:
            self.stdout.write(self.style.WARNING('Nenhuma tabela de clientes encontrada. Pulando.'))
            return 0

        count = 0
        for item in dados:
            nome = item.get('nome') or item.get('name', '')
            if not nome:
                continue

            cidade_nome = item.get('cidade') or item.get('cidade_nome') or item.get('city', '')
            cidade_estado = item.get('estado') or item.get('uf') or ''

            cidade = None
            if cidade_nome:
                cidade, _ = Cidade.objects.get_or_create(
                    nome_cidade=cidade_nome,
                    estado=str(cidade_estado)[:2],
                    empresa=empresa,
                )
            else:
                cidade = Cidade.objects.filter(empresa=empresa).first()
                if not cidade:
                    cidade, _ = Cidade.objects.get_or_create(
                        nome_cidade='Nao Informada',
                        estado='NA',
                        empresa=empresa,
                    )

            telefone = item.get('telefone') or item.get('phone') or item.get('celular', '')
            email = item.get('email', '')
            endereco = item.get('endereco') or item.get('address', '')
            ativo = item.get('ativo', True)
            if isinstance(ativo, str):
                ativo = ativo.lower() in ('true', '1', 'sim', 'yes')
            contato = item.get('contato') or item.get('contact', '')
            conexao = item.get('conexao') or item.get('connection', '')
            obs = item.get('obs') or item.get('observacoes') or item.get('notes', '')

            valor_mens = item.get('valor_mensalidade') or item.get('mensalidade')
            dia_cob = item.get('dia_cobranca') or item.get('dia')

            cliente, created = Cliente.objects.update_or_create(
                nome=nome,
                empresa=empresa,
                defaults={
                    'telefone': telefone,
                    'email': email,
                    'endereco': endereco,
                    'ativo': bool(ativo),
                    'contato': contato,
                    'conexao': conexao,
                    'obs': obs,
                    'cidade': cidade,
                    'valor_mensalidade': valor_mens,
                    'dia_cobranca': dia_cob,
                }
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} clientes importados.'))
        return count

    def _importar_parcelas(self, empresa):
        self.stdout.write('Importando parcelas/contas a receber...')

        dados = self._query_table('parcelas')
        if dados is None:
            dados = self._query_table('contas')
        if dados is None:
            dados = self._query_table('contas_receber')
        if dados is None:
            self.stdout.write(self.style.WARNING('Nenhuma tabela de parcelas encontrada. Pulando.'))
            return 0

        count = 0
        for item in dados:
            cliente_id_supa = item.get('cliente_id') or item.get('cliente') or item.get('client_id')
            cliente_nome = item.get('cliente_nome') or item.get('nome_cliente') or item.get('client_name', '')

            cliente = None
            if cliente_id_supa:
                try:
                    cliente = Cliente.objects.get(id=int(cliente_id_supa), empresa=empresa)
                except (ValueError, Cliente.DoesNotExist):
                    pass
            if not cliente and cliente_nome:
                cliente = Cliente.objects.filter(nome__icontains=cliente_nome, empresa=empresa).first()
            if not cliente:
                self.stdout.write(self.style.WARNING(f'  Cliente nao encontrado para parcela: {item}'))
                continue

            numero = item.get('numero_parcela') or item.get('numero') or item.get('number', '')
            total = item.get('total_parcelas') or item.get('total') or 1
            valor = item.get('valor_parcela') or item.get('valor') or item.get('amount', 0)
            data_venc_str = item.get('data_vencimento') or item.get('vencimento') or item.get('due_date', '')
            status_str = (item.get('status') or 'ABERTA').upper()

            status_map = {
                'ABERTA': StatusParcela.ABERTA, 'OPEN': StatusParcela.ABERTA, 'PENDENTE': StatusParcela.ABERTA,
                'LIQUIDADA': StatusParcela.LIQUIDADA, 'PAGA': StatusParcela.LIQUIDADA, 'PAID': StatusParcela.LIQUIDADA, 'PAGO': StatusParcela.LIQUIDADA,
                'CANCELADA': StatusParcela.CANCELADA, 'CANCELLED': StatusParcela.CANCELADA, 'CANCELADA': StatusParcela.CANCELADA,
            }
            status = status_map.get(status_str, StatusParcela.ABERTA)

            data_pag_str = item.get('data_pagamento') or item.get('pagamento') or item.get('payment_date')
            valor_pago = item.get('valor_pago') or item.get('paid_amount')
            cobranca_uuid = item.get('cobranca_uuid') or item.get('uuid') or item.get('group_id')

            data_venc = None
            if data_venc_str:
                try:
                    from datetime import datetime
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S'):
                        try:
                            data_venc = datetime.strptime(str(data_venc_str)[:10], fmt).date()
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            data_pag = None
            if data_pag_str:
                try:
                    from datetime import datetime
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
                        try:
                            data_pag = datetime.strptime(str(data_pag_str)[:10], fmt).date()
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            if not data_venc:
                from datetime import date
                data_venc = date.today()

            Parcela.objects.create(
                cobranca_uuid=str(cobranca_uuid) if cobranca_uuid else None,
                cliente=cliente,
                numero_parcela=str(numero),
                total_parcelas=int(total),
                valor_parcela=Decimal(str(valor)),
                data_vencimento=data_venc,
                status=status,
                data_pagamento=data_pag,
                valor_pago=Decimal(str(valor_pago)) if valor_pago else None,
                empresa=empresa,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} parcelas importadas.'))
        return count

    def handle(self, *args, **options):
        self._base_url = options.get('supabase_url') or settings.SUPABASE_URL
        self._service_key = options.get('supabase_key') or settings.SUPABASE_SERVICE_KEY

        if not self._base_url:
            self.stdout.write(self.style.ERROR('SUPABASE_URL nao configurada. Defina no .env ou use --supabase-url.'))
            return

        empresa_id = options['empresa_id']
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'Empresa id={empresa_id} nao existe. Criando empresa padrao...'))
            empresa = Empresa.objects.create(id=empresa_id, nome='Empresa Padrao')

        tabela = options.get('tabela', 'todas')

        self.stdout.write(self.style.SUCCESS(f'Iniciando importacao do Supabase: {self._base_url}'))
        self.stdout.write(f'Empresa: {empresa.nome} (ID: {empresa.id})')
        self.stdout.write('')

        if tabela in ('cidades', 'todas'):
            self._importar_cidades(empresa)

        if tabela in ('clientes', 'todas'):
            self._importar_clientes(empresa)

        if tabela in ('parcelas', 'todas'):
            self._importar_parcelas(empresa)

        self.stdout.write(self.style.SUCCESS('\nImportacao concluida!'))
